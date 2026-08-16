# -------------------------------------------------------
# app/schemas/request.py
# Cấu trúc JSON nhận từ CRM hoặc Client (Request Bodies)
# -------------------------------------------------------
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional


# ─── 1. Sales Call Submission ──────────────────────────────────────────────────
class SalesCallRequest(BaseModel):
    """CRM → AI: Gửi recording của cuộc gọi sales call để phân tích"""
    customer_id: str = Field(..., description="ID khách hàng trong CRM")
    customer_name: str = Field(..., description="Tên khách hàng")
    customer_phone: Optional[str] = None
    customer_zalo_id: Optional[str] = None
    customer_email: Optional[str] = None
    audio_url: HttpUrl = Field(..., description="URL nội bộ hoặc public đến file ghi âm")
    salesperson_id: Optional[str] = None


# ─── 2. HR Candidate Submission ────────────────────────────────────────────────
class CandidateAnalyzeRequest(BaseModel):
    """CRM → AI: Gửi recording phỏng vấn ứng viên để phân tích (Thay thế AnalyzeRequest cũ)"""
    ssn: str = Field(..., description="Số CCCD/CMND hoặc mã số định danh của ứng viên")
    candidate_name: str = Field(..., description="Tên ứng viên")
    audio_url: HttpUrl = Field(..., description="URL nội bộ hoặc public đến file ghi âm")


# ─── 3. Follow-up Config ───────────────────────────────────────────────────────
class FollowUpConfigRequest(BaseModel):
    """Salesperson → AI: Bật/tắt trạng thái hoạt động của một follow-up task cụ thể"""
    task_id: str = Field(..., description="ID của follow-up task cần cấu hình")
    is_enabled: bool = Field(..., description="Trạng thái bật (True) hoặc tắt (False)")