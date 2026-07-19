# -------------------------------------------------------
# app/api/dependencies.py
# Quản lý dependency injection (VD: auth, db session)
# -------------------------------------------------------
# TODO: get_settings() → return Settings instance
# TODO: get_llm_service() → return LLMService singleton
# TODO: (Future) get_db_session() → return DB session
# TODO: (Future) verify_api_key() → auth dependency
# -------------------------------------------------------
# -------------------------------------------------------
# app/api/dependencies.py
# Quản lý dependency injection (auth, db session, settings, llm)
# -------------------------------------------------------
from typing import Generator
from fastapi import Depends, Header, status
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings, Settings
from app.core.database import SessionLocal
from app.services.llm_service import llm_service, LLMService


def get_settings() -> Settings:
    """Trả về instance Settings dùng chung (đã load từ .env)."""
    return settings


def get_llm_service() -> LLMService:
    """Trả về LLMService singleton đã được load ở startup (main.py)."""
    return llm_service


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency cấp DB session theo từng request, tự đóng session sau khi
    response trả về (kể cả khi có exception).

    Dùng cho các endpoint đồng bộ (không phải background task — trong
    process_candidate_audio hiện đang tự gọi SessionLocal() trực tiếp vì
    chạy ngoài vòng đời request/response của FastAPI).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(x_api_key: str = Header(default=None)) -> None:
    """
    Auth dependency đơn giản dựa trên header X-API-Key, so sánh với
    settings.SECRET_KEY.

    ⚠️ Lưu ý: settings hiện dùng chung SECRET_KEY cho việc này — nếu cần
    tách riêng khóa API cho CRM gọi vào (khác với secret dùng nội bộ,
    ví dụ ký JWT sau này), nên thêm field `API_KEY` riêng trong
    core/config.py rồi đổi so sánh bên dưới cho tương ứng.
    """
    if not settings.SECRET_KEY or settings.SECRET_KEY == "change-me":
        # Chưa cấu hình secret thật trong .env -> coi như auth đang tắt (dev mode)
        return

    if x_api_key != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key không hợp lệ hoặc thiếu header X-API-Key.",
        )