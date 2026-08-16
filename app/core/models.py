import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class CallStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FollowUpStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContextType(str, enum.Enum):
    SALES = "sales"          # Follow-up khách hàng sau sales call
    HR = "hr"                # Follow-up ứng viên sau phỏng vấn


class CallRecord(Base):
    """
    Lưu thông tin mỗi cuộc gọi được submit để xử lý.
    Dùng chung cho cả Sales call và HR interview.
    """
    __tablename__ = "call_records"

    id = Column(String, primary_key=True, default=lambda: f"TASK-{uuid.uuid4().hex[:8]}")
    context_type = Column(Enum(ContextType), nullable=False, default=ContextType.SALES)

    # Thông tin contact
    contact_id = Column(String, nullable=True)   # customer_id hoặc candidate_ssn
    contact_name = Column(String, nullable=False)
    contact_phone = Column(String, nullable=True)
    contact_zalo_id = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)

    # Audio
    audio_url = Column(String, nullable=False)

    # Kết quả STT & LLM
    transcript = Column(Text, nullable=True)
    intent = Column(String, nullable=True)         # detected intent
    sentiment = Column(String, nullable=True)      # positive / neutral / negative
    summary = Column(Text, nullable=True)
    recommended_message = Column(Text, nullable=True)

    # Trạng thái xử lý
    status = Column(Enum(CallStatus), default=CallStatus.PENDING)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ
    followup_tasks = relationship("FollowUpTask", back_populates="call_record", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="call_record", cascade="all, delete-orphan")


class FollowUpTask(Base):
    """
    Lịch gửi follow-up message theo schedule D+1, D+3, D+7.
    """
    __tablename__ = "followup_tasks"

    id = Column(String, primary_key=True, default=lambda: f"FU-{uuid.uuid4().hex[:8]}")
    call_record_id = Column(String, ForeignKey("call_records.id"), nullable=False)

    # Schedule
    day_offset = Column(Integer, nullable=False)   # 1, 3, hoặc 7
    scheduled_at = Column(DateTime, nullable=False)

    # Channel: zalo | facebook | email
    channel = Column(String, nullable=False, default="zalo")

    # Nội dung
    message_content = Column(Text, nullable=True)
    action_suggestion = Column(Text, nullable=True)  # gợi ý hành động cho Sales

    # Trạng thái
    status = Column(Enum(FollowUpStatus), default=FollowUpStatus.SCHEDULED)
    sent_at = Column(DateTime, nullable=True)
    delivery_status = Column(String, nullable=True)  # raw response từ channel
    error_message = Column(Text, nullable=True)

    # Config: Sales có thể bật/tắt từng task
    is_enabled = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ
    call_record = relationship("CallRecord", back_populates="followup_tasks")


class AuditLog(Base):
    """
    Lưu lịch sử đánh giá và quyết định của hệ thống AI/Rule Engine.
    """
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: f"AUDIT-{uuid.uuid4().hex[:8]}")
    call_record_id = Column(String, ForeignKey("call_records.id"), nullable=False)

    action = Column(String, nullable=False)  # Ví dụ: "LLM_ANALYSIS", "RULE_EVALUATION"
    decision = Column(Text, nullable=False)  # Tóm tắt quyết định
    details = Column(Text, nullable=True)     # Raw JSON data or prompt

    created_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ
    call_record = relationship("CallRecord", back_populates="audit_logs")