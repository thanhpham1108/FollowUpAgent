# -------------------------------------------------------
# app/schemas/response.py
# Cấu trúc JSON trả về CRM (Webhook payload)
# -------------------------------------------------------
# Models:
#
# 1. TaskAcceptedResponse (trả về ngay khi nhận request)
#   - task_id: str       → "TASK-a1b2c3d4"
#   - status: str        → "processing"
#   - message: str       → "Audio received and is being processed..."
#
# 2. AnalysisResult (kết quả phân tích từ LLM)
#   - summary: str               → Tóm tắt cuộc phỏng vấn
#   - recommended_message: str   → Tin nhắn follow-up gợi ý
#
# 3. WebhookPayload (gửi về CRM qua webhook)
#   - task_id: str
#   - ssn: str
#   - status: str                → "completed" | "failed"
#   - result: AnalysisResult?
#   - error: str?
#
# 4. HealthResponse
#   - status: str
#   - uptime_seconds: float
#   - llm_ready: bool
#
from pydantic import BaseModel
from typing import Optional

class TaskAcceptedResponse(BaseModel):
    task_id: str
    status: str
    message: str

class AnalysisResult(BaseModel):
    summary: str
    recommended_message: str

class WebhookPayload(BaseModel):
    task_id: str
    ssn: str
    status: str
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    llm_ready: bool# -------------------------------------------------------
