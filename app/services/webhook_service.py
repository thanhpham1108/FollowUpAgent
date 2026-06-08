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
