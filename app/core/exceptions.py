# -------------------------------------------------------
# app/core/exceptions.py
# Cấu hình xử lý lỗi chung (Custom Error Handlers)
# -------------------------------------------------------
# Custom Exceptions:
#   - AudioDownloadError    : Lỗi tải audio từ CRM
#   - AudioValidationError  : Audio sai định dạng hoặc quá lớn
#   - LLMProcessingError    : LLM xử lý thất bại
#   - WebhookDeliveryError  : Gửi webhook về CRM thất bại
#
# FastAPI Exception Handlers:
#   - Trả về structured JSON error response
#   - Log chi tiết lỗi
#
# TODO: Implement exception classes & handlers
# -------------------------------------------------------
