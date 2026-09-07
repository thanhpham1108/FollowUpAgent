# -------------------------------------------------------
# app/schemas/response.py
# Cấu trúc JSON trả về CRM hoặc Dashboard (Response / Webhook Payloads)
# -------------------------------------------------------
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── 1. Phản hồi tức thời khi nhận Request (API Responses) ─────────────────────────
class SalesCallResponse(BaseModel):
    """Trả về ngay sau khi nhận Sales Call Request để xử lý bất đồng bộ"""
    task_id: str = Field(..., description="Mã task xử lý (Ví dụ: TASK-a1b2c3d4)")
    status: str = Field("processing", description="Trạng thái ban đầu")
    message: str = Field("Audio received and is being processed...", description="Thông báo hệ thống")


class CandidateAnalyzeResponse(BaseModel):
    """Trả về ngay sau khi nhận HR Candidate Request để xử lý bất đồng bộ"""
    task_id: str = Field(..., description="Mã task xử lý (Ví dụ: TASK-a1b2c3d4)")
    status: str = Field("processing", description="Trạng thái ban đầu")
    message: str = Field("Audio received and is being processed...", description="Thông báo hệ thống")


class TaskStatusResponse(BaseModel):
    """Phản hồi cho API tra cứu trạng thái task (Polling)"""
    task_id: str = Field(..., description="Mã task xử lý")
    status: str = Field(..., description="pending | processing | completed | failed | webhook_failed")
    contact_name: Optional[str] = Field(None, description="Tên liên hệ / ứng viên")
    summary: Optional[str] = Field(None, description="Tóm tắt cuộc gọi (chỉ có khi completed)")
    intent: Optional[str] = Field(None, description="Mã phân loại ý định (reason_code)")
    recommended_message: Optional[str] = Field(None, description="Tin nhắn gợi ý follow-up")
    error_message: Optional[str] = Field(None, description="Thông báo lỗi (chỉ có khi failed)")
    created_at: Optional[datetime] = Field(None, description="Thời điểm tạo task")


# ─── 2. Cấu trúc kết quả phân tích từ LLM ───────────────────────────────────────
class AnalysisResult(BaseModel):
    """Chi tiết kết quả xử lý từ mô hình AI (STT & LLM)"""
    summary: str = Field(..., description="Tóm tắt cuộc gọi/phỏng vấn")
    status_group: int = Field(..., description="Thuộc nhóm trạng thái nào (1 đến 5)")
    reason_code: str = Field(..., description="Mã lý do chi tiết (Ví dụ: KNM_1, SUY_NGHI_THEM, CHO_CCCD)")
    appointment_date: Optional[str] = Field(None, description="Ngày hẹn thực tế nếu thuộc Nhóm 4")
    recommended_message: str = Field(..., description="Tin nhắn follow-up gợi ý cho kênh tương tác")


# ─── 3. Webhook Payloads (AI → CRM) ─────────────────────────────────────────────
class SalesWebhookResult(BaseModel):
    """AI → CRM: Kết quả phân tích cuộc gọi Sales gửi qua Webhook"""
    task_id: str
    customer_id: str
    status: str = Field(..., description="completed | failed")
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None


class HRWebhookResult(BaseModel):
    """AI → CRM: Kết quả phân tích phỏng vấn HR gửi qua Webhook"""
    task_id: str
    ssn: str
    status: str = Field(..., description="completed | failed")
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None


# ─── 4. Cấu trúc chi tiết hiển thị cho Dashboard / Client ──────────────────────────
class FollowUpTaskSchema(BaseModel):
    """Chi tiết về một lịch trình gửi tin nhắn follow-up (D+1, D+3, D+7)"""
    id: str
    day_offset: int
    scheduled_at: datetime
    channel: str
    message_content: Optional[str] = None
    action_suggestion: Optional[str] = None
    status: str
    is_enabled: bool

    class Config:
        from_attributes = True  # Hỗ trợ tự động parse từ SQLAlchemy Model ở Pydantic v2


class CallRecordDetailSchema(BaseModel):
    """Thông tin tổng quan của một cuộc gọi kèm danh sách các follow-up tasks liên quan"""
    id: str
    context_type: str  # sales | hr
    contact_name: str
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    intent: Optional[str] = None
    status: str
    followup_tasks: List[FollowUpTaskSchema] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ─── 5. Kiểm tra trạng thái hệ thống (Health Check) ──────────────────────────────
class HealthResponse(BaseModel):
    """Trả về trạng thái hoạt động của Service và các Model liên quan"""
    status: str = Field("healthy")
    uptime_seconds: float
    llm_ready: bool