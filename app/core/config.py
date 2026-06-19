# -------------------------------------------------------
# app/core/config.py
# Load biến môi trường (ENV) cho hệ thống
# -------------------------------------------------------
# Sử dụng Pydantic BaseSettings để tự động đọc từ .env
#
# Các biến cần cấu hình:
#   - WEBHOOK_URL        : URL webhook của CRM
#   - LLM_MODEL_PATH     : Đường dẫn tới file model GGUF
#   - AUDIO_DOWNLOAD_DIR : Thư mục tạm chứa audio (default: ./data)
#   - MAX_AUDIO_SIZE_MB  : Giới hạn kích thước audio (default: 500)
#   - WEBHOOK_MAX_RETRIES: Số lần retry webhook (default: 3)
#   - WEBHOOK_RETRY_BACKOFF: Thời gian chờ cơ bản (default: 1.0s)
#   - LOG_LEVEL          : Mức log (default: INFO)
#   - ALLOWED_AUDIO_EXTENSIONS: Định dạng audio cho phép
#
# TODO: Implement Settings class
# -------------------------------------------------------
from pydantic_settings import BaseSettings
from typing import List, Union


class Settings(BaseSettings):
    # App chung
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = "change-me"
    LOG_LEVEL: str = "INFO"  # <-- Thêm theo yêu cầu comment

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/followup_agent"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Audio & Thư mục tạm (Bổ sung theo yêu cầu comment)
    AUDIO_DOWNLOAD_DIR: str = "./data"
    MAX_AUDIO_SIZE_MB: int = 500
    # Có thể để List[str] hoặc str. Nếu dùng .env thì str tiện phân tách bằng dấu phẩy
    ALLOWED_AUDIO_EXTENSIONS: Union[str, List[str]] = "mp3,wav,m4a,ogg"

    # CRM Webhooks & Retry (Bổ sung đầy đủ theo yêu cầu comment)
    WEBHOOK_URL: str = ""  # Gốc yêu cầu WEBHOOK_URL
    CRM_WEBHOOK_URL: str = ""
    CRM_SALES_WEBHOOK_URL: str = ""
    WEBHOOK_MAX_RETRIES: int = 3
    WEBHOOK_RETRY_BACKOFF: float = 1.0

    # AI Models (Whisper, Ollama & GGUF Local)
    LLM_MODEL_PATH: str = ""  # <-- Thêm đường dẫn file GGUF theo yêu cầu comment
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Zalo
    ZALO_OA_ACCESS_TOKEN: str = ""
    ZALO_OA_ID: str = ""

    # Follow-up schedule
    FOLLOWUP_SCHEDULE_DAYS: str = "1,3,7"

    @property
    def followup_days(self) -> List[int]:
        return [int(d.strip()) for d in self.FOLLOWUP_SCHEDULE_DAYS.split(",")]

    @property
    def allowed_extensions_list(self) -> List[str]:
        if isinstance(self.ALLOWED_AUDIO_EXTENSIONS, list):
            return self.ALLOWED_AUDIO_EXTENSIONS
        return [ext.strip().lower() for ext in self.ALLOWED_AUDIO_EXTENSIONS.split(",")]

    # Cấu hình Pydantic v2 (Khuyên dùng thay cho class Config cũ)
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


# Khởi tạo một instance duy nhất để import và dùng toàn bộ project
settings = Settings()