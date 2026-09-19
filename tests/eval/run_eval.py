# -------------------------------------------------------
# tests/eval/run_eval.py
# Script chính để chạy Evaluation Pipeline
# -------------------------------------------------------
# Chạy: python -m tests.eval.run_eval
#
# Yêu cầu:
#   - Ollama đang chạy với 2 model: qwen2.5:7b-instruct + llama3.1
#   - Thư mục gốc phải là /Users/macos/Desktop/BK/URA/Datacore
# -------------------------------------------------------
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Setup path để import được app.* ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.llm_service import llm_service
from tests.eval.judge import llm_judge

# ── Logging cơ bản (chỉ in WARNING trở lên để console không rối) ─────────────
logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("eval")

DATASET_PATH = Path(__file__).parent / "dataset" / "samples.json"
REPORT_DIR = Path(__file__).parent / "reports"


# ── Helper: In bảng kết quả ra console ───────────────────────────────────────
def _print_header():
    print("\n" + "=" * 80)
    print("  FollowUpAgent — LLM-as-a-Judge Evaluation Report")
    print(f"  Worker : qwen2.5:7b-instruct  |  Judge : llama3.1")
    print(f"  Run at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


def _print_row(
    idx: int,
    case_id: str,
    expected_group: int,
    actual_group: Optional[int],
    expected_code: str,
    actual_code: Optional[str],
    group_match: bool,
    code_match: bool,
    hallucination: Optional[int],
    logic: Optional[int],
):
    group_icon = "✅" if group_match else "❌"
    code_icon = "✅" if code_match else "❌"
    h_str = f"{hallucination}/5" if hallucination is not None else "N/A"
    l_str = f"{logic}/5" if logic is not None else "N/A"

    print(
        f"  [{idx:02d}] {case_id:<30}"
        f"  Group: {group_icon} ({expected_group}→{actual_group})"
        f"  Code: {code_icon} ({expected_code}→{actual_code})"
        f"  Hallucination: {h_str}  Logic: {l_str}"
    )


def _print_critique(case_id: str, critique: Optional[str]):
    if critique:
        print(f"\n       └─ [Judge Critique | {case_id}]")
        for line in critique.splitlines():
            print(f"          {line}")
        print()


# ── Hàm chạy 1 sample ─────────────────────────────────────────────────────────
async def _run_single_sample(sample: dict) -> dict:
    """
    Chạy 1 sample qua Qwen2.5 (Worker) rồi Llama3.1 (Judge).
    Trả về dict kết quả để tổng hợp báo cáo.
    """
    case_id = sample["id"]
    transcript = sample["transcript"]
    contact_name = sample["contact_name"]
    expected_group = sample["expected_status_group"]
    expected_code = sample["expected_reason_code"]

    # ── Bước 1: Gọi Worker (Qwen2.5) ──────────────────────────────────────────
    worker_output = None
    worker_error = None
    try:
        analysis = await llm_service.analyze_audio(
            transcript=transcript,
            contact_name=contact_name,
            context_type="hr",
        )
        worker_output = analysis.model_dump()
    except Exception as e:
        worker_error = str(e)
        logger.warning(f"[{case_id}] Worker lỗi: {e}")

    actual_group = worker_output.get("status_group") if worker_output else None
    actual_code = worker_output.get("reason_code") if worker_output else None

    group_match = actual_group == expected_group
    code_match = actual_code == expected_code if actual_code else False

    # ── Bước 2: Gọi Judge (Llama3.1) ──────────────────────────────────────────
    judge_result = None
    if worker_output:
        judge_result = llm_judge.evaluate(
            transcript=transcript,
            ai_output=worker_output,
        )

    return {
        "case_id": case_id,
        "expected_status_group": expected_group,
        "actual_status_group": actual_group,
        "expected_reason_code": expected_code,
        "actual_reason_code": actual_code,
        "group_match": group_match,
        "code_match": code_match,
        "worker_output": worker_output,
        "worker_error": worker_error,
        "hallucination_score": judge_result["hallucination_score"] if judge_result else None,
        "logic_score": judge_result["logic_score"] if judge_result else None,
        "critique": judge_result["critique"] if judge_result else None,
    }


# ── Main ───────────────────────────────────────────────────────────────────────
async def main():
    # Tiền kiểm tra
    print("\n[Pre-check] Kiểm tra Judge Model (llama3.1)...", end=" ")
    if not llm_judge.check_availability():
        print("FAILED")
        print("\n⚠️  Judge Model chưa sẵn sàng. Chạy lệnh sau để tải:")
        print("    ollama pull llama3.1\n")
        sys.exit(1)
    print("OK ✅")

    # Load dataset
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        samples = json.load(f)

    print(f"[Info] Bắt đầu eval {len(samples)} samples...")
    _print_header()

    results = []
    for idx, sample in enumerate(samples, start=1):
        print(f"\n  Đang xử lý [{idx:02d}/{len(samples)}] {sample['id']}...", end=" ", flush=True)
        result = await _run_single_sample(sample)
        results.append(result)
        print("done")

        _print_row(
            idx=idx,
            case_id=result["case_id"],
            expected_group=result["expected_status_group"],
            actual_group=result["actual_status_group"],
            expected_code=result["expected_reason_code"],
            actual_code=result["actual_reason_code"],
            group_match=result["group_match"],
            code_match=result["code_match"],
            hallucination=result["hallucination_score"],
            logic=result["logic_score"],
        )
        _print_critique(result["case_id"], result["critique"])

    # ── Tổng hợp điểm ─────────────────────────────────────────────────────────
    total = len(results)
    group_correct = sum(1 for r in results if r["group_match"])
    code_correct = sum(1 for r in results if r["code_match"])

    judge_samples = [r for r in results if r["hallucination_score"] is not None]
    avg_hallucination = (
        sum(r["hallucination_score"] for r in judge_samples) / len(judge_samples)
        if judge_samples else None
    )
    avg_logic = (
        sum(r["logic_score"] for r in judge_samples) / len(judge_samples)
        if judge_samples else None
    )

    print("\n" + "=" * 80)
    print("  TỔNG KẾT")
    print("=" * 80)
    print(f"  📊 Deterministic (Exact Match)")
    print(f"     Status Group Accuracy : {group_correct}/{total} ({group_correct/total*100:.1f}%)")
    print(f"     Reason Code Accuracy  : {code_correct}/{total} ({code_correct/total*100:.1f}%)")
    print()
    print(f"  🤖 Judge Score (Llama3.1 chấm Qwen2.5)")
    if avg_hallucination is not None:
        print(f"     Avg Hallucination Score : {avg_hallucination:.2f}/5.00  {'🟢' if avg_hallucination >= 4 else '🟡' if avg_hallucination >= 3 else '🔴'}")
        print(f"     Avg Logic Score         : {avg_logic:.2f}/5.00  {'🟢' if avg_logic >= 4 else '🟡' if avg_logic >= 3 else '🔴'}")
    else:
        print("     Không có dữ liệu Judge (Judge Model lỗi hoặc chưa chạy)")
    print("=" * 80)

    # ── Lưu report ra file markdown ───────────────────────────────────────────
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "run_at": datetime.now().isoformat(),
                "worker_model": "qwen2.5:7b-instruct",
                "judge_model": "llama3.1",
                "summary": {
                    "total": total,
                    "group_accuracy": f"{group_correct/total*100:.1f}%",
                    "code_accuracy": f"{code_correct/total*100:.1f}%",
                    "avg_hallucination": round(avg_hallucination, 2) if avg_hallucination else None,
                    "avg_logic": round(avg_logic, 2) if avg_logic else None,
                },
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\n  📄 Full report saved: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
