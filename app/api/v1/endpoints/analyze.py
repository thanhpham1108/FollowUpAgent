# -------------------------------------------------------
# app/api/v1/endpoints/analyze.py
# API nhận request phân tích audio từ CRM
# -------------------------------------------------------
# Endpoint: POST /candidates/analyze
#
# Flow:
#   1. Nhận AnalyzeRequest (ssn, candidate_name, audio_url)
#   2. Tạo task_id unique (format: TASK-{uuid})
#   3. Validate request
#   4. Dispatch background task:
#      a. Download audio  → audio_service
#      b. Phân tích audio → llm_service
#      c. Gửi webhook     → webhook_service
#      d. Dọn dẹp file    → file_manager
#   5. Return 202 Accepted với task_id
#
import uuid
import asyncio
from fastapi import APIRouter, BackgroundTasks, status
from app.schemas.request import AnalyzeRequest
from app.schemas.response import TaskAcceptedResponse

router = APIRouter()

async def mock_background_processing(task_id: str, ssn: str, audio_url: str):
    """
    Hàm giả lập xử lý ngầm (Mock pipeline).
    """
    print(f"[Task {task_id}] Bắt đầu xử lý audio cho ứng viên SSN: {ssn}")
    print(f"[Task {task_id}] Đang tải audio từ: {audio_url}")
    await asyncio.sleep(2) # Giả lập thời gian tải file
    print(f"[Task {task_id}] Đang phân tích bằng LLM...")
    await asyncio.sleep(5) # Giả lập thời gian chạy LLM
    print(f"[Task {task_id}] Hoàn thành phân tích. Gửi webhook về CRM...")
    await asyncio.sleep(1) # Giả lập thời gian gọi webhook
    print(f"[Task {task_id}] Task kết thúc thành công.")


@router.post("/analyze", response_model=TaskAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_candidate_audio(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks
):
    # Tạo task_id duy nhất
    task_id = f"TASK-{uuid.uuid4().hex[:8]}"
    
    # Đưa tác vụ vào hàng chờ chạy ngầm
    background_tasks.add_task(
        mock_background_processing,
        task_id=task_id,
        ssn=request.ssn,
        audio_url=str(request.audio_url)
    )
    
    # Trả về kết quả ngay lập tức
    return TaskAcceptedResponse(
        task_id=task_id,
        status="processing",
        message="Audio received and is being processed in the background."
    )
