import logging
import json
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import CallRecord, FollowUpTask, AuditLog, FollowUpStatus
from app.schemas.response import AnalysisResult

logger = logging.getLogger(__name__)

class RuleEngineService:
    async def evaluate_rules(self, call_record: CallRecord, analysis: AnalysisResult, db: AsyncSession) -> None:
        """
        Đánh giá kết quả từ AI, gán Rule tương ứng, tạo FollowUpTask và ghi AuditLog.
        Tất cả thao tác DB đều là bất đồng bộ (async/await).
        """
        logger.info(f"Đang chạy Rule Engine cho CallRecord ID: {call_record.id}")

        status_group = analysis.status_group
        reason_code = analysis.reason_code
        now = datetime.utcnow()
        scheduled_at = None
        action_desc = ""

        # Logic tính Dateline theo 5 nhóm chuẩn nghiệp vụ
        if status_group == 1:
            # Nhóm 1: Đóng hồ sơ / Bỏ qua (TU_CHOI_LUON, KNM_DAP_MAY, SAI_SO_NHAM_SO) -> KHÔNG GỌI LẠI
            scheduled_at = None
            action_desc = f"Gán Rule Nhóm 1 ({reason_code}): Đóng hồ sơ, KHÔNG LÊN LỊCH GỌI LẠI"

        elif status_group == 2:
            # Nhóm 2: Gián đoạn / Cần gọi lại (KHACH_BAN, CUOC_GOI_RONG, LOI_AM_THANH)
            if reason_code == "KHACH_BAN":
                scheduled_at = now + timedelta(hours=2)
                action_desc = f"Gán Rule Nhóm 2 ({reason_code}): Khách bận, nhắc HR gọi lại sau 2 giờ"
            else:
                scheduled_at = now + timedelta(minutes=15)
                action_desc = f"Gán Rule Nhóm 2 ({reason_code}): Gián đoạn kết nối, nhắc HR gọi lại sau 15 phút"

        elif status_group == 3:
            # HEN_XA follows the agreed interval; other potential candidates get 3 days.
            days = (analysis.follow_up_days or 7) if reason_code == "HEN_XA" else 3
            scheduled_at = now + timedelta(days=days)
            action_desc = f"Gán Rule Nhóm 3 ({reason_code}): HR liên hệ lại sau {days} ngày"

        elif status_group == 4:
            # Nhóm 4: Đã có lịch phỏng vấn (HEN_PHONG_VAN)
            if analysis.appointment_date:
                try:
                    # Date-only appointment: remind HR at 09:00 Vietnam time the previous day.
                    appt_day = date.fromisoformat(analysis.appointment_date)
                    reminder_local = datetime.combine(
                        appt_day - timedelta(days=1), time(9, 0),
                        tzinfo=timezone(timedelta(hours=7))
                    )
                    scheduled_at = reminder_local.astimezone(timezone.utc).replace(tzinfo=None)
                    if scheduled_at < now:
                        scheduled_at = now + timedelta(hours=1)
                    action_desc = f"Gán Rule Nhóm 4: Nhắc nhở trước ngày hẹn phỏng vấn ({analysis.appointment_date})"
                except Exception:
                    scheduled_at = now + timedelta(days=1)
                    action_desc = "Gán Rule Nhóm 4: Format ngày không hợp lệ, set mặc định 1 ngày"
            else:
                scheduled_at = now + timedelta(days=1)
                action_desc = "Gán Rule Nhóm 4: Không có ngày hẹn cụ thể, set mặc định 1 ngày"

        elif status_group == 5:
            # Nhóm 5: Đã chốt đi làm (DI_LAM)
            scheduled_at = now + timedelta(days=2)
            action_desc = "Gán Rule Nhóm 5: Đã chốt đi làm, cập nhật theo dõi sau 2 ngày"

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
                message_content=None,
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

        # Lưu thay đổi (async)
        await db.commit()
        logger.info(f"Hoàn tất Rule Engine cho CallRecord ID: {call_record.id}")

rule_engine_service = RuleEngineService()
