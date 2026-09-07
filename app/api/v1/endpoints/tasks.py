# -------------------------------------------------------
# app/api/v1/endpoints/tasks.py
# API tra cứu trạng thái xử lý task (Polling)
# -------------------------------------------------------
import logging
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.schemas.response import TaskStatusResponse
from app.core.database import SessionLocal
from app.core.models import CallRecord

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Tra cứu trạng thái xử lý của một task theo task_id.
    CRM sử dụng endpoint này để kiểm tra tiến trình (Polling).

    Trả về:
    - pending: Đang chờ trong hàng đợi
    - processing: Đang xử lý (STT / LLM)
    - completed: Hoàn thành, kết quả đã gửi về CRM
    - failed: Pipeline xử lý gặp lỗi
    - webhook_failed: Phân tích xong nhưng gửi Webhook thất bại
    """
    async with SessionLocal() as db:
        result = await db.execute(
            select(CallRecord).where(CallRecord.id == task_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy task với mã: {task_id}"
            )

        return TaskStatusResponse(
            task_id=record.id,
            status=record.status.value,
            contact_name=record.contact_name,
            summary=record.summary,
            intent=record.intent,
            recommended_message=record.recommended_message,
            error_message=record.error_message,
            created_at=record.created_at
        )
