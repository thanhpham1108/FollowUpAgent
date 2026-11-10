#!/usr/bin/env python3
"""Create a review CSV from local WAV files using PhoWhisper and the HR LLM."""

import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# Resolve paths from this script so the command works from any working directory.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
sys.path.append(str(BACKEND_ROOT))
from app.classification.llm import ClassificationNeedsReview

DEFAULT_AUDIO_DIR = REPO_ROOT / "data/recordings_import/audio"
DEFAULT_OUTPUT_CSV = REPO_ROOT / "data/recordings_import/ground_truth_review_713_merged.csv"
DEFAULT_EXPECTED_COUNT = 713

COLUMNS = [
    "File_Name",
    "Transcript_Cleaned",
    "AI_Status_Group",
    "AI_Reason_Code",
    "AI_Call_Decision",
    "AI_Appointment_Date",
    "AI_Follow_Up_Days",
    "AI_Summary",
    "Human_Status_Group (Điền tay)",
    "Human_Reason_Code (Điền tay)",
]
ERROR_COLUMNS = ["Time", "File_Name", "Error"]
MAX_CONSECUTIVE_ERRORS = 5


def read_completed(output_csv: Path) -> set[str]:
    """Read successful rows and reject incompatible or ambiguous CSVs."""
    with output_csv.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"CSV {output_csv} không đúng cấu trúc cột của script hiện tại")
        completed: set[str] = set()
        for row in reader:
            name = row["File_Name"]
            if not name or name in completed:
                raise ValueError(f"CSV {output_csv} có File_Name trống hoặc trùng: {name!r}")
            if not row["AI_Reason_Code"] or row["Transcript_Cleaned"].startswith("Lỗi:"):
                raise ValueError(f"CSV {output_csv} có dòng lỗi cũ ({name}); dùng output mới với --resume")
            completed.add(name)
    return completed


def log_error(error_csv: Path, file_name: str, error: Exception) -> None:
    """Keep a historical error/review log; missing success rows are retried on resume."""
    exists = error_csv.exists()
    with error_csv.open("a" if exists else "x", encoding="utf-8" if exists else "utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        if not exists:
            writer.writerow(ERROR_COLUMNS)
        writer.writerow([datetime.now().isoformat(timespec="seconds"), file_name, str(error)])


async def main(
    audio_dir: Path = DEFAULT_AUDIO_DIR,
    output_csv: Path = DEFAULT_OUTPUT_CSV,
    limit: int = 0,
    resume: bool = True,
    expected_count: int | None = None,
    transcribe_fn=None,
    analyze_fn=None,
) -> int:
    wav_files = sorted(audio_dir.glob("*.wav"))
    if not wav_files:
        print(f"Không tìm thấy file .wav nào trong {audio_dir}.", file=sys.stderr)
        return 2
    if expected_count is not None and len(wav_files) != expected_count:
        print(
            f"Số WAV không khớp: thấy {len(wav_files)}, mong đợi {expected_count}. "
            "Kiểm tra tải audio trước khi gán nhãn.",
            file=sys.stderr,
        )
        return 2

    available_names = {path.name for path in wav_files}
    if limit > 0:
        wav_files = wav_files[:limit]

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if output_csv.exists() and not resume:
        output_csv = output_csv.with_name(
            f"{output_csv.stem}_{datetime.now():%Y%m%d_%H%M%S}{output_csv.suffix}"
        )

    try:
        completed = read_completed(output_csv) if output_csv.exists() else set()
    except (OSError, ValueError) as exc:
        print(f"Không thể tiếp tục: {exc}", file=sys.stderr)
        return 2
    unknown = completed - available_names
    if unknown:
        print(f"CSV chứa file không nằm trong {audio_dir}: {sorted(unknown)[0]}", file=sys.stderr)
        return 2

    if transcribe_fn is None:
        from app.audio.service import transcribe_audio

        transcribe_fn = transcribe_audio
    if analyze_fn is None:
        from app.classification.llm import llm_service

        analyze_fn = llm_service.analyze_audio

    mode = "a" if output_csv.exists() else "x"
    encoding = "utf-8" if mode == "a" else "utf-8-sig"
    error_csv = output_csv.with_name(f"{output_csv.stem}_error_log.csv")
    trace_path = output_csv.with_name(f"{output_csv.stem}_decision_trace.jsonl")
    failures = 0
    review_rows = 0
    consecutive_errors = 0
    done_before = sum(path.name in completed for path in wav_files)
    print(f"[*] {len(wav_files)} WAV; đã hoàn thành {done_before}; output: {output_csv}", flush=True)

    with output_csv.open(mode, encoding=encoding, newline="") as handle, trace_path.open("a", encoding="utf-8") as trace_handle:
        writer = csv.writer(handle)
        if mode == "x":
            writer.writerow(COLUMNS)
            handle.flush()

        for index, wav_file in enumerate(wav_files, 1):
            if wav_file.name in completed:
                print(f"[{index}/{len(wav_files)}] Đã có: {wav_file.name}", flush=True)
                continue
            print(f"[{index}/{len(wav_files)}] Đang phân tích: {wav_file.name}", flush=True)
            needs_review_fallback = False
            summary_review_reason = ""

            def trace_event(event: dict) -> None:
                nonlocal needs_review_fallback, summary_review_reason
                if event.get("event") == "fallback" and event.get("requires_review"):
                    needs_review_fallback = True
                if event.get("event") == "summary_review":
                    summary_review_reason = event.get("reason") or "Summary có dữ kiện cốt lõi chưa xác minh."
                trace_handle.write(json.dumps({
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "file_name": wav_file.name,
                    **event,
                }, ensure_ascii=False) + "\n")
                trace_handle.flush()

            try:
                stt_result = transcribe_fn(wav_file)
                transcript = stt_result["text"].strip()
                analysis = await analyze_fn(
                    transcript,
                    contact_name="Ứng viên",
                    audio_duration_seconds=stt_result.get("duration_seconds"),
                    trace_callback=trace_event,
                )
                writer.writerow([
                    wav_file.name,
                    transcript,
                    analysis.status_group,
                    analysis.reason_code,
                    analysis.call_decision,
                    analysis.appointment_date,
                    analysis.follow_up_days,
                    analysis.summary,
                    "",
                    "",
                ])
                handle.flush()
                completed.add(wav_file.name)
                consecutive_errors = 0
                if needs_review_fallback or summary_review_reason:
                    review_rows += 1
                    review_note = (
                        "Nhãn tạm TRAO_DOI_THEM: lời từ chối chưa được xác minh. "
                        if needs_review_fallback else ""
                    ) + (summary_review_reason or "Cần nghe lại quyết định cuối của ứng viên.")
                    log_error(
                        error_csv, wav_file.name,
                        ClassificationNeedsReview(f"Cần nghe lại audio: {review_note}"),
                    )
                    print(f"   -> CẦN NGHE LẠI: {wav_file.name} ({review_note})", flush=True)
                print(
                    f"   -> Nhóm {analysis.status_group} ({analysis.reason_code}) | "
                    f"Quyết định: {analysis.call_decision}",
                    flush=True,
                )
                print(f"   -> Summary: {analysis.summary[:100]}...", flush=True)
            except ClassificationNeedsReview as exc:
                failures += 1
                consecutive_errors = 0
                trace_event({"event": "batch_error", "outcome": "needs_review", "error": str(exc)})
                log_error(error_csv, wav_file.name, exc)
                print(f"   -> CẦN NGHE LẠI: {exc}", file=sys.stderr, flush=True)
            except Exception as exc:
                failures += 1
                consecutive_errors += 1
                trace_event({"event": "batch_error", "outcome": "error", "error": str(exc)})
                print(f"   -> LỖI: {exc}", file=sys.stderr, flush=True)
                if resume:
                    log_error(error_csv, wav_file.name, exc)
                else:
                    writer.writerow([wav_file.name, f"Lỗi: {exc}"] + [""] * (len(COLUMNS) - 2))
                    handle.flush()
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print(f"Dừng sau {MAX_CONSECUTIVE_ERRORS} lỗi liên tiếp; kiểm tra Ollama/STT rồi chạy lại.", file=sys.stderr)
                    break

    done = sum(path.name in completed for path in wav_files)
    print(
        f"[+] Hoàn thành {done}/{len(wav_files)} WAV; lỗi lượt này: {failures}; "
        f"dòng cần nghe lại: {review_rows}; CSV: {output_csv}"
    )
    return 0 if done == len(wav_files) and failures == 0 else 1


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Chạy STT và LLM để tạo CSV cho người gán nhãn kiểm tra")
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR, help="Thư mục chứa các file .wav")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_CSV, help="CSV kết quả")
    parser.add_argument("--limit", type=int, default=0, help="Số file đầu tiên cần xử lý; 0 là tất cả")
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True,
                        help="Tiếp tục CSV hiện có; dùng --no-resume để tạo file mới")
    parser.add_argument("--expected-count", type=int, help="Số WAV mong đợi trong thư mục trước khi bắt đầu")
    args = parser.parse_args(argv)
    if args.limit < 0 or (args.expected_count is not None and args.expected_count <= 0):
        parser.error("--limit phải >= 0 và --expected-count phải > 0")
    if args.expected_count is None and args.audio_dir.resolve() == DEFAULT_AUDIO_DIR:
        args.expected_count = DEFAULT_EXPECTED_COUNT
    return args


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(main(args.audio_dir, args.output, args.limit, args.resume, args.expected_count)))
