# -------------------------------------------------------
# app/services/webhook_service.py
# Logic call HTTP POST trả kết quả về CRM
# -------------------------------------------------------
# Function:
#
# async deliver_webhook(payload: WebhookPayload) -> bool
#   1. POST WebhookPayload dưới dạng JSON tới WEBHOOK_URL
#   2. Retry với exponential backoff (1s → 2s → 4s)
#   3. Log chi tiết success/failure
#   4. Return True nếu thành công, False nếu hết retry
#
# Không raise exception — chỉ log và trả về status
#
# Config (từ .env):
#   - WEBHOOK_URL
#   - WEBHOOK_MAX_RETRIES (default: 3)
#   - WEBHOOK_RETRY_BACKOFF (default: 1.0s)
#
# TODO: Implement webhook delivery
# -------------------------------------------------------
# -------------------------------------------------------
# app/services/webhook_service.py
# Logic call HTTP POST trả kết quả về CRM & Gửi Message các kênh
# -------------------------------------------------------
import asyncio
import httpx
import logging
from typing import Union
from pydantic import BaseModel
from app.core.config import settings

# Import các Schema cần dùng để hỗ trợ kiểm tra kiểu dữ liệu hoặc ép kiểu JSON trực tiếp
try:
    from app.schemas.response import WebhookPayload, SalesWebhookResult, HRWebhookResult
except ImportError:
    WebhookPayload = dict
    SalesWebhookResult = dict
    HRWebhookResult = dict

logger = logging.getLogger(__name__)


# ─── 1. Logic Lõi Webhook Delivery với Exponential Backoff ───────────────────

async def deliver_webhook(
    payload: Union[WebhookPayload, SalesWebhookResult, HRWebhookResult, dict], 
    target_url: str = None
) -> bool:
    """
    1. POST WebhookPayload dưới dạng JSON tới target_url (mặc định lấy settings.WEBHOOK_URL).
    2. Retry với exponential backoff (1s → 2s → 4s → ... tùy thuộc cấu hình nhân số mũ).
    3. Log chi tiết trạng thái success/failure.
    4. Trả về True nếu gửi thành công, False nếu hết lượt retry mà vẫn lỗi.
    
    *Nguyên tắc:* Không raise exception ra bên ngoài — chỉ log và trả về status bool.
    """
    # Xác định URL đích, nếu không truyền cụ thể thì ưu tiên lấy WEBHOOK_URL mặc định
    url = target_url or settings.WEBHOOK_URL
    if not url:
        logger.error("Không thể gửi Webhook: WEBHOOK_URL chưa được cấu hình trong hệ thống.")
        return False

    # Chuyển đổi payload sang dict nếu client truyền vào dạng Pydantic Model
    json_data = payload.model_dump() if isinstance(payload, BaseModel) else payload

    max_retries = settings.WEBHOOK_MAX_RETRIES
    base_backoff = settings.WEBHOOK_RETRY_BACKOFF

    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Đang gửi Webhook tới {url} (Lần thử {attempt}/{max_retries})...")
                response = await client.post(url, json=json_data)
                
                # Trực tiếp kích hoạt HTTPStatusError nếu trả về mã lỗi 4xx hoặc 5xx
                response.raise_for_status()
                
                logger.info(f"Gửi Webhook thành công! CRM phản hồi mã trạng thái: {response.status_code}")
                return True

            except (httpx.HTTPError, Exception) as e:
                logger.warning(f"Lần thử thứ {attempt} thất bại do lỗi: {e}")
                
                # Nếu chưa tới giới hạn lần thử cuối cùng, thực hiện chờ tăng dần theo cấp số mũ
                if attempt < max_retries:
                    sleep_time = base_backoff * (2 ** (attempt - 1))
                    logger.info(f"Sẽ thử lại sau {sleep_time} giây...")
                    await asyncio.sleep(sleep_time)
                else:
                    logger.error(f"Gửi Webhook thất bại hoàn toàn sau {max_retries} lần thử liên tiếp.")

    return False


# ─── 2. Wrappers Định Tuyến Phù Hợp Cho Luồng Nghiệp Vụ ─────────────────────

async def notify_crm_sales_webhook(payload: dict) -> bool:
    """
    Gửi kết quả phân tích + lịch follow-up về CRM (Sales flow) qua cơ chế backoff.
    """
    url = settings.CRM_SALES_WEBHOOK_URL or settings.WEBHOOK_URL
    if not settings.CRM_SALES_WEBHOOK_URL:
        logger.warning("CRM_SALES_WEBHOOK_URL chưa được cấu hình, sử dụng WEBHOOK_URL mặc định.")
        
    return await deliver_webhook(payload=payload, target_url=url)


async def notify_crm_hr_webhook(payload: dict) -> bool:
    """
    Gửi kết quả phân tích về CRM (HR flow) qua cơ chế backoff.
    """
    url = settings.CRM_WEBHOOK_URL or settings.WEBHOOK_URL
    if not settings.CRM_WEBHOOK_URL:
        logger.warning("CRM_WEBHOOK_URL chưa được cấu hình, sử dụng WEBHOOK_URL mặc định.")
        
    return await deliver_webhook(payload=payload, target_url=url)


# ─── 3. Logic Gửi Tin Nhắn Đa Kênh (Zalo, Email, ...) ───────────────────────

async def send_zalo_message(zalo_user_id: str, message: str) -> dict:
    """Gửi tin nhắn phản hồi CSKH qua Zalo OA API."""
    url = "https://openapi.zalo.me/v3.0/oa/message/cs"
    headers = {
        "access_token": settings.ZALO_OA_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    payload = {
        "recipient": {"user_id": zalo_user_id},
        "message": {"text": message},
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Zalo đã gửi tới khách hàng {zalo_user_id}: {data}")
            return {"success": True, "response": data}
        except httpx.HTTPError as e:
            logger.error(f"Gửi Zalo thất bại: {e}")
            return {"success": False, "error": str(e)}


async def send_zalo_friend_request(phone: str) -> dict:
    """Gửi lời mời kết bạn Zalo qua số điện thoại nếu chưa có zalo_id."""
    url = "https://openapi.zalo.me/v2.0/oa/message"
    headers = {"access_token": settings.ZALO_OA_ACCESS_TOKEN}
    payload = {
        "phone": phone,
        "template_id": "friend_request",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            data = resp.json()
            return {"success": True, "response": data}
        except Exception as e:
            logger.error(f"Gửi lời mời kết bạn Zalo qua SĐT thất bại: {e}")
            return {"success": False, "error": str(e)}


async def send_email(to_email: str, subject: str, body: str) -> dict:
    """Placeholder: Gửi email qua SMTP hoặc dịch vụ mail nội bộ của công ty."""
    logger.info(f"[EMAIL MOCKUP] To: {to_email} | Subject: {subject}")
    # TODO: Cấu hình với thư viện smtplib khi kết nối máy chủ Mail thực tế
    return {"success": True, "channel": "email", "note": "placeholder"}


async def send_message(channel: str, contact_info: dict, message: str) -> dict:
    """Hàm trung chuyển (Router) lựa chọn kênh liên lạc phù hợp dựa trên thông tin sẵn có."""
    if channel == "zalo" and contact_info.get("zalo_id"):
        return await send_zalo_message(contact_info["zalo_id"], message)

    elif channel == "zalo" and contact_info.get("phone"):
        # Chiến lược dự phòng: dùng SĐT gửi tin (Zalo OA CS yêu cầu user liên hệ trước hoặc dùng SĐT)
        return await send_zalo_message(contact_info["phone"], message)

    elif channel == "email" and contact_info.get("email"):
        return await send_email(
            contact_info["email"],
            subject="Thông tin liên hệ tự động hệ thống",
            body=message,
        )
    else:
        logger.warning(f"Không tìm thấy thông tin liên lạc hợp lệ cho kênh={channel}: {contact_info}")
        return {"success": False, "error": "No valid contact info"}