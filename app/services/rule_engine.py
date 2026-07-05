import logging
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.models import CallRecord, FollowUpTask, AuditLog, FollowUpStatus
from app.schemas.response import AnalysisResult

logger = logging.getLogger(__name__)

class RuleEngineService:
    def evaluate_rules(self, call_record: CallRecord, analysis: AnalysisResult, db: Session) -> None:
        """
        Đánh giá kết quả từ AI, gán Rule tương ứng, tạo FollowUpTask và ghi AuditLog.
        """
        logger.info(f"Đang chạy Rule Engine cho CallRecord ID: {call_record.id}")

        status_group = analysis.status_group
        reason_code = analysis.reason_code
        now = datetime.utcnow()
        scheduled_at = None
        action_desc = ""

        # Logic tính Dateline
        if status_group == 1:
            # Nhóm 1: Chưa tư vấn -> 10 phút
            scheduled_at = now + timedelta(minutes=10)
            action_desc = "Gán Rule Nhóm 1: Nhắc HR gọi điện trong 10 phút"
            
        elif status_group == 2:
            # Nhóm 2: Cần gọi lại
            if reason_code in ["KNM_1", "KNM_2", "KNM_3"]:
                scheduled_at = now + timedelta(days=1)
                action_desc = f"Gán Rule Nhóm 2 (Lý do: {reason_code}): Nhắc HR gọi lại sau 1 ngày"
            else:
                scheduled_at = now + timedelta(days=3)
                action_desc = f"Gán Rule Nhóm 2 (Lý do: {reason_code}): Nhắc HR gọi lại sau 3 ngày"
                
        elif status_group == 3:
            # Nhóm 3: UV Tiềm năng
            scheduled_at = now + timedelta(days=3)
            action_desc = f"Gán Rule Nhóm 3 (Lý do: {reason_code}): Nhắc HR chăm sóc sau 3 ngày"
            
        elif status_group == 4:
            # Nhóm 4: Hẹn phỏng vấn
            if analysis.appointment_date:
                try:
                    # Giả định appointment_date dạng YYYY-MM-DD
                    appt_date = datetime.strptime(analysis.appointment_date, "%Y-%m-%d")
                    # Lên lịch nhắc nhở 1 ngày trước lịch hẹn (hoặc đúng ngày tùy nghiệp vụ)
                    scheduled_at = appt_date - timedelta(days=1)
                    if scheduled_at < now:
                        scheduled_at = now + timedelta(hours=1)
                    action_desc = f"Gán Rule Nhóm 4: Nhắc nhở theo ngày hẹn thực tế ({analysis.appointment_date})"
                except Exception:
                    scheduled_at = now + timedelta(days=1)
                    action_desc = "Gán Rule Nhóm 4: Format ngày không hợp lệ, set mặc định 1 ngày"
            else:
                scheduled_at = now + timedelta(days=1)
                action_desc = "Gán Rule Nhóm 4: Không có ngày hẹn, set mặc định 1 ngày"
                
        elif status_group == 5:
            # Nhóm 5: Đi làm tạm tính
            scheduled_at = now + timedelta(days=2)
            action_desc = "Gán Rule Nhóm 5: Đã nhận việc, cập nhật sau 2 ngày"
            
        else:
            scheduled_at = now + timedelta(days=1)
            action_desc = f"Không xác định được nhóm ({status_group}), set mặc định 1 ngày"

        # 1. Ghi nhận FollowUpTask
        if scheduled_at:
            task = FollowUpTask(
                call_record_id=call_record.id,
                day_offset=(scheduled_at - now).days,
                scheduled_at=scheduled_at,
                channel="zalo",
                message_content=analysis.recommended_message,
                status=FollowUpStatus.SCHEDULED,
                is_enabled=True
            )
            db.add(task)

        # 2. Ghi AuditLog
        audit_details = {
            "input_group": status_group,
            "input_reason": reason_code,
            "scheduled_at": scheduled_at.isoformat() if scheduled_at else None
        }
        
        audit_log = AuditLog(
            call_record_id=call_record.id,
            action="RULE_EVALUATION",
            decision=action_desc,
            details=json.dumps(audit_details, ensure_ascii=False)
        )
        db.add(audit_log)
        
        # Lưu thay đổi
        db.commit()
        logger.info(f"Hoàn tất Rule Engine cho CallRecord ID: {call_record.id}")

rule_engine_service = RuleEngineService()
