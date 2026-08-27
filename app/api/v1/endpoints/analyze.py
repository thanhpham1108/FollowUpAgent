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
import logging
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, status
from app.schemas.request import CandidateAnalyzeRequest
from app.schemas.response import CandidateAnalyzeResponse
from app.services.audio_service import speech_to_text
from app.services.llm_service import llm_service
from app.services.webhook_service import notify_crm_hr_webhook
from app.services.rule_engine import rule_engine_service
from app.core.database import SessionLocal
from app.core.models import CallRecord, CallStatus, ContextType, AuditLog

logger = logging.getLogger(__name__)

router = APIRouter()


async def process_candidate_audio(task_id: str, request: CandidateAnalyzeRequest):
    """
    Hàm xử lý ngầm pipeline hoàn chỉnh: Audio -> LLM -> DB -> Webhook.
    Sử dụng AsyncSession cho toàn bộ thao tác với database.
    """
    logger.info(f"[Task {task_id}] Bắt đầu xử lý audio cho ứng viên SSN: {request.ssn}")

    async with SessionLocal() as db:
        try:
            # 1. Khởi tạo record trong DB
            record = CallRecord(
                id=task_id,
                context_type=ContextType.HR,
                contact_id=request.ssn,
                contact_name=request.candidate_name,
                audio_url=str(request.audio_url),
                status=CallStatus.PROCESSING
            )
            db.add(record)
            await db.commit()

            # 2. Download & STT (Audio Service)
            logger.info(f"[Task {task_id}] Đang tải và dịch audio từ: {request.audio_url}")
            transcript = await speech_to_text(str(request.audio_url), task_id)

            record.transcript = transcript
            await db.commit()

            # 3. Phân tích ngữ nghĩa (LLM Service)
            logger.info(f"[Task {task_id}] Đang phân tích bằng LLM...")
            analysis_result = await llm_service.analyze_audio(
                transcript=transcript,
                contact_name=request.candidate_name,
                context_type="hr"
            )

            record.summary = analysis_result.summary
            record.recommended_message = analysis_result.recommended_message
            record.intent = analysis_result.reason_code
            record.status = CallStatus.COMPLETED
            # Wire các field còn thiếu từ kết quả LLM
            if analysis_result.appointment_date:
                record.updated_at = datetime.utcnow()
            await db.commit()

            # Ghi AuditLog sau bước LLM
            audit_llm = AuditLog(
                call_record_id=task_id,
                action="LLM_ANALYSIS",
                decision=f"status_group={analysis_result.status_group}, reason_code={analysis_result.reason_code}",
                details=analysis_result.model_dump_json()
            )
            db.add(audit_llm)
            await db.commit()

            # 3.5 Chạy Rule Engine
            logger.info(f"[Task {task_id}] Gọi Rule Engine sinh lịch Follow-up...")
            await rule_engine_service.evaluate_rules(call_record=record, analysis=analysis_result, db=db)

            # Ghi AuditLog sau bước Rule Engine
            audit_rule = AuditLog(
                call_record_id=task_id,
                action="RULE_EVALUATION",
                decision=f"Follow-up tasks scheduled for contact {request.ssn}",
                details=f"{{\"status_group\": {analysis_result.status_group}, \"appointment_date\": \"{analysis_result.appointment_date}\"}}"
            )
            db.add(audit_rule)
            await db.commit()

            logger.info(f"[Task {task_id}] Hoàn thành phân tích. Gửi webhook về CRM...")
            webhook_payload = {
                "task_id": task_id,
                "ssn": request.ssn,
                "status": "completed",
                "result": analysis_result.model_dump()
            }
            await notify_crm_hr_webhook(webhook_payload)
            logger.info(f"[Task {task_id}] Task kết thúc thành công.")

        except Exception as e:
            logger.error(f"[Task {task_id}] Xảy ra lỗi trong quá trình xử lý: {e}")
            record.status = CallStatus.FAILED
            record.error_message = str(e)
            await db.commit()

            # Gửi webhook lỗi
            webhook_payload = {
                "task_id": task_id,
                "ssn": request.ssn,
                "status": "failed",
                "error": str(e)
            }
            await notify_crm_hr_webhook(webhook_payload)


@router.post("/analyze", response_model=CandidateAnalyzeResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_candidate_audio(
    request: CandidateAnalyzeRequest,
    background_tasks: BackgroundTasks
):
    # Tạo task_id duy nhất
    task_id = f"TASK-{uuid.uuid4().hex[:8]}"

    # Đưa tác vụ vào hàng chờ chạy ngầm
    background_tasks.add_task(
        process_candidate_audio,
        task_id=task_id,
        request=request
    )

    # Trả về kết quả ngay lập tức
    return CandidateAnalyzeResponse(
        task_id=task_id,
        status="processing",
        message="Audio received and is being processed in the background."
    )
