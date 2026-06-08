# -------------------------------------------------------
# app/utils/logger.py
# Cấu hình log để debug trên máy ảo
# -------------------------------------------------------
# Format: [timestamp] [level] [module] message
#
# Handlers:
#   - Console handler  (stdout)
#   - Rotating file handler (logs/followup_agent.log)
#
# Config:
#   - Log level đọc từ config.py (LOG_LEVEL)
#   - Max file size: 10MB, backup count: 5
#
# Function:
#   get_logger(name: str) -> Logger
#     → Factory để tạo logger cho từng module
#
# TODO: Implement logger configuration
# -------------------------------------------------------
