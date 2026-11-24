#!/usr/bin/env python3
"""Score existing call decisions against human labels without running STT or Ollama."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from zipfile import BadZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.classification.codes import GROUP_CALL_DECISION, REASON_CODE_GROUP, CallDecision


ACTION_BY_REASON = {code.value: GROUP_CALL_DECISION[group] for code, group in REASON_CODE_GROUP.items()}
ACTIONS = tuple(action.value for action in CallDecision)
HUMAN_COLUMNS = {
    "reason": ("Human_Reason_Code (chọn)", "Human_Reason_Code (Điền tay)", "Human_Reason_Code"),
    "review": ("Review Flag (chọn nếu cần)", "Review Flag", "Review_Flag"),
}
AI_COLUMNS = {
    "reason": ("AI_Reason_Code",),
    "action": ("AI_Call_Decision",),
    "transcript": ("Transcript_Cleaned",),
}
CASE_COLUMNS = (
    "File_Name", "Human_Reason_Code", "Human_Action", "AI_Reason_Code", "AI_Action",
    "AI_Outcome", "AI_Needs_Review", "Human_Review_Flag", "Issues",
)


def cell_text(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_sheet(path: Path, rows: Iterable, columns: dict) -> dict[str, dict[str, str]]:
    """Find the header below any Excel title rows and index records by exact filename."""
    rows = iter(rows)
    for header_line, row in enumerate(rows, start=1):
        header = [cell_text(value) for value in row]
        if "File_Name" in header:
            break
    else:
        raise ValueError(f"{path}: thiếu cột File_Name")

    indexes = {"name": header.index("File_Name")}
    for key, aliases in columns.items():
        matches = [index for index, value in enumerate(header) if value in aliases]
        if len(matches) > 1:
            raise ValueError(f"{path}: có nhiều cột khớp với {aliases[0]}")
        if matches:
            indexes[key] = matches[0]
    if "reason" not in indexes:
        raise ValueError(f"{path}: thiếu cột {columns['reason'][0]}")
    if header.count("File_Name") > 1:
        raise ValueError(f"{path}: trùng cột File_Name")

    records = {}
    for line, row in enumerate(rows, start=header_line + 1):
        values = {key: cell_text(row[index]) if index < len(row) else "" for key, index in indexes.items()}
        name = values.pop("name")
        if not name:
            if any(values.values()):
                raise ValueError(f"{path}:{line}: dòng kết quả thiếu File_Name")
            continue
        if name in records:
            raise ValueError(f"{path}:{line}: File_Name bị trùng: {name}")
        records[name] = values
    return records


def read_labels(path: Path, columns: dict) -> dict[str, dict[str, str]]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return read_sheet(path, csv.reader(handle, strict=True), columns)
    if path.suffix.lower() != ".xlsx":
        raise ValueError(f"{path}: chỉ nhận file .csv hoặc .xlsx")
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ValueError("Cần openpyxl để đọc Excel: python -m pip install openpyxl") from exc

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook["Labeling"] if "Labeling" in workbook.sheetnames else workbook.worksheets[0]
        return read_sheet(path, sheet.iter_rows(values_only=True), columns)
    finally:
        workbook.close()


def read_trace(path: Path | None) -> dict[str, dict]:
    """Keep the last outcome per file. Earlier retries may have failed."""
    outcomes = {}
    if path is not None:
        with path.open(encoding="utf-8-sig") as handle:
            for number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except ValueError as exc:
                    raise ValueError(f"{path}:{number}: JSONL không hợp lệ") from exc
                if not isinstance(event, dict) or not isinstance(event.get("file_name"), str):
                    raise ValueError(f"{path}:{number}: event thiếu file_name")
                if event.get("event") == "batch_error" or (
                    event.get("event") == "final" and event.get("outcome") == "accepted"
                ):
                    outcomes[event["file_name"]] = event
    return outcomes


def read_errors(path: Path | None) -> dict[str, str]:
    errors = {}
    if path is not None:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            if not {"File_Name", "Error"}.issubset(reader.fieldnames or ()):
                raise ValueError(f"{path}: cần hai cột File_Name và Error")
            for row in reader:
                errors[cell_text(row["File_Name"])] = cell_text(row["Error"])
    return errors


def review_signal(trace: dict, error: str, valid: bool) -> bool | None:
    if trace.get("outcome") == "accepted" and valid:
        signal = trace.get("requires_review")
        if isinstance(signal, bool):
            return signal
    if not valid and trace.get("event") == "batch_error":
        return trace.get("outcome") == "needs_review"
    if "cần nghe lại" in error.casefold():
        return True
    return None


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def reason_scores(matrix: Counter) -> dict:
    scores = {}
    for reason in ACTION_BY_REASON:
        tp = matrix[reason, reason]
        support = sum(matrix[reason, predicted] for predicted in ACTION_BY_REASON)
        predicted_count = sum(matrix[actual, reason] for actual in ACTION_BY_REASON)
        scores[reason] = {
            "support": support, "predicted": predicted_count, "correct": tp,
            "precision": ratio(tp, predicted_count),
            "recall": ratio(tp, support),
            "f1": ratio(2 * tp, support + predicted_count),
        }
    return scores


def score(humans: dict, predictions: dict, traces: dict, errors: dict):
    counts, outcomes = Counter(), Counter()
    reason_matrix, action_matrix = Counter(), Counter()
    cases = []
    for name, human in humans.items():
        human_reason = human["reason"]
        human_action = ACTION_BY_REASON.get(human_reason, "")
        if human_reason and not human_action:
            raise ValueError(f"{name}: nhãn người ngoài taxonomy: {human_reason}")

        prediction = predictions.get(name, {})
        ai_reason = prediction.get("reason", "")
        expected_ai_action = ACTION_BY_REASON.get(ai_reason, "")
        ai_action = prediction.get("action", expected_ai_action)
        valid = bool(expected_ai_action and ai_action in ACTIONS)
        trace = traces.get(name, {})
        error = errors.get(name, "")
        review = review_signal(trace, error, valid)

        if valid:
            outcome = "scored"
        elif review:
            outcome = "needs_review"
        elif trace.get("event") == "batch_error" or error or prediction.get("transcript", "").startswith("Lỗi:"):
            outcome = "error"
        else:
            outcome = "invalid" if prediction else "missing"

        issues = []
        if outcome != "scored":
            issues.append(f"ai_{outcome}")
        if review:
            issues.append("ai_needs_review")
        if human.get("review"):
            issues.append("human_review_flag")
        if valid and ai_action != expected_ai_action:
            issues.append("ai_action_mapping_mismatch")

        if human_reason:
            counts["labeled"] += 1
            counts["review_flagged"] += review is True
            counts["review_status_known"] += review is not None
            counts["human_review_flagged"] += bool(human.get("review"))
            outcomes[outcome] += 1
            if human_action != CallDecision.NO_CALL.value:
                counts["human_non_no_call"] += 1
            if valid:
                reason_matrix[human_reason, ai_reason] += 1
                action_matrix[human_action, ai_action] += 1
                if ai_reason != human_reason:
                    issues.append("reason_mismatch")
                if ai_action != human_action:
                    issues.append("action_mismatch")
                if human_action != CallDecision.NO_CALL.value:
                    counts["scored_non_no_call"] += 1
                    if ai_action == CallDecision.NO_CALL.value:
                        issues.append("incorrect_no_call")
                        counts["incorrect_no_call"] += 1
                        counts["incorrect_no_call_tu_choi_luon"] += ai_reason == "TU_CHOI_LUON"
                counts["action_mapping_mismatches"] += ai_action != expected_ai_action

        if issues and (human_reason or prediction or trace or error or human.get("review")):
            cases.append((
                name, human_reason, human_action, ai_reason, ai_action, outcome,
                "" if review is None else str(review).lower(), human.get("review", ""), "|".join(issues),
            ))

    labeled, scored = counts["labeled"], outcomes["scored"]
    per_reason = reason_scores(reason_matrix)
    f1s = [item["f1"] for item in per_reason.values() if item["f1"] is not None]
    action_correct = sum(action_matrix[action, action] for action in ACTIONS)
    reason_correct = sum(reason_matrix[reason, reason] for reason in ACTION_BY_REASON)
    report = {
        "files": {
            "human_total": len(humans),
            "human_labeled": labeled,
            "human_unlabeled": len(humans) - labeled,
            "ai_total": len(predictions),
            "ai_outside_human_file_list": sorted(predictions.keys() - humans.keys()),
            "ai_on_labeled_files": dict.fromkeys(("scored", "needs_review", "error", "invalid", "missing"), 0)
            | dict(outcomes),
        },
        "coverage": ratio(scored, labeled),
        "action_correct": action_correct,
        "action_accuracy": ratio(action_correct, scored),
        "reason_correct": reason_correct,
        "reason_accuracy": ratio(reason_correct, scored),
        "reason_macro_f1": ratio(sum(f1s), len(f1s)),
        "incorrect_no_call": {
            "count": counts["incorrect_no_call"],
            "tu_choi_luon_count": counts["incorrect_no_call_tu_choi_luon"],
            "human_non_no_call": counts["human_non_no_call"],
            "scored_non_no_call": counts["scored_non_no_call"],
            "observed_rate_among_all_labeled_non_no_call": ratio(
                counts["incorrect_no_call"], counts["human_non_no_call"]
            ),
            "rate_among_scored_non_no_call": ratio(counts["incorrect_no_call"], counts["scored_non_no_call"]),
        },
        "review": {
            "ai_flagged": counts["review_flagged"],
            "ai_status_known": counts["review_status_known"],
            "ai_status_unknown": labeled - counts["review_status_known"],
            "ai_flagged_rate_among_known": ratio(counts["review_flagged"], counts["review_status_known"]),
            "human_flagged": counts["human_review_flagged"],
        },
        "action_mapping_mismatches": counts["action_mapping_mismatches"],
        "per_reason": per_reason,
    }
    return report, reason_matrix, action_matrix, cases


def write_csv(path: Path, header: Iterable, rows: Iterable) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def write_confusion(path: Path, labels: Iterable, matrix: Counter) -> None:
    labels = tuple(labels)
    write_csv(path, ("Human / AI", *labels), (
        (actual, *(matrix[actual, predicted] for predicted in labels)) for actual in labels
    ))


def sidecar(path: Path | None, ai_csv: Path, suffix: str) -> Path | None:
    if path is not None:
        return path
    default = ai_csv.with_name(ai_csv.stem + suffix)
    return default if default.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--human", required=True, type=Path, help="Excel hoặc CSV có nhãn người")
    parser.add_argument("--ai", required=True, type=Path, help="CSV kết quả AI")
    parser.add_argument("--out-dir", required=True, type=Path, help="Thư mục ghi báo cáo")
    parser.add_argument("--trace", type=Path, help="Decision trace JSONL; mặc định tìm cạnh CSV AI")
    parser.add_argument("--error-log", type=Path, help="Error log CSV; mặc định tìm cạnh CSV AI")
    args = parser.parse_args()

    try:
        trace = sidecar(args.trace, args.ai, "_decision_trace.jsonl")
        error_log = sidecar(args.error_log, args.ai, "_error_log.csv")
        report, reason_matrix, action_matrix, cases = score(
            read_labels(args.human, HUMAN_COLUMNS),
            read_labels(args.ai, AI_COLUMNS),
            read_trace(trace),
            read_errors(error_log),
        )
        report["inputs"] = {
            "human": str(args.human), "ai": str(args.ai),
            "trace": str(trace) if trace else None, "error_log": str(error_log) if error_log else None,
        }
        paths = {
            key: args.out_dir / name for key, name in (
                ("reason", "reason_confusion.csv"), ("action", "action_confusion.csv"),
                ("cases", "cases_to_review.csv"), ("metrics", "metrics.json"),
            )
        }
        inputs = {p.resolve() for p in (args.human, args.ai, trace, error_log) if p is not None}
        if any(path.resolve() in inputs for path in paths.values()):
            raise ValueError("Thư mục đích sẽ ghi đè một file đầu vào.")

        args.out_dir.mkdir(parents=True, exist_ok=True)
        write_confusion(paths["reason"], ACTION_BY_REASON, reason_matrix)
        write_confusion(paths["action"], ACTIONS, action_matrix)
        write_csv(paths["cases"], CASE_COLUMNS, cases)
        paths["metrics"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, csv.Error, BadZipFile) as exc:
        print(f"Lỗi chấm offline: {exc}", file=sys.stderr)
        return 2

    files = report["files"]
    scored = files["ai_on_labeled_files"]["scored"]
    print(f"Đã chấm {scored}/{files['human_labeled']} file có nhãn người. Báo cáo: {args.out_dir}")
    if not scored:
        print("Chưa có cặp nhãn người và kết quả AI hợp lệ để tính điểm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
