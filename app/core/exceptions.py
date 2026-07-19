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
# -------------------------------------------------------
# app/core/exceptions.py
# Cấu hình xử lý lỗi chung (Custom Error Handlers)
# -------------------------------------------------------
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppBaseException(Exception):
    """Lớp cơ sở cho mọi exception nghiệp vụ, mang theo status_code & error_code chuẩn hóa."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = None):
        self.message = message or self.__class__.__doc__ or "Đã có lỗi xảy ra."
        super().__init__(self.message)


class AudioDownloadError(AppBaseException):
    """Lỗi tải audio từ CRM (network, HTTP status lỗi, timeout...)."""
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "AUDIO_DOWNLOAD_ERROR"


class AudioValidationError(AppBaseException):
    """Audio sai định dạng hoặc vượt quá kích thước cho phép."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "AUDIO_VALIDATION_ERROR"


class LLMProcessingError(AppBaseException):
    """LLM (model GGUF cục bộ) xử lý thất bại hoặc chưa sẵn sàng."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "LLM_PROCESSING_ERROR"


class WebhookDeliveryError(AppBaseException):
    """Gửi webhook về CRM thất bại sau khi hết số lần retry."""
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "WEBHOOK_DELIVERY_ERROR"


def register_exception_handlers(app: FastAPI) -> None:
    """
    Đăng ký exception handler dùng chung cho toàn app trong main.py:
        from app.core.exceptions import register_exception_handlers
        register_exception_handlers(app)
    Đảm bảo mọi lỗi trả về JSON structured thay vì traceback thô cho client.
    """

    @app.exception_handler(AppBaseException)
    async def app_exception_handler(request: Request, exc: AppBaseException):
        logger.error(f"[{exc.error_code}] {request.method} {request.url.path} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Lỗi không xác định tại {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "Đã có lỗi hệ thống xảy ra, vui lòng thử lại sau.",
                "path": str(request.url.path),
            },
        )