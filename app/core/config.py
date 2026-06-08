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
