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
# -------------------------------------------------------
# app/utils/logger.py
# -------------------------------------------------------
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

_LOG_DIR = Path("logs")
_LOG_FILE = _LOG_DIR / "followup_agent.log"
_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5
_configured = False


def _configure_root_logger() -> None:
    global _configured
    if _configured:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if root_logger.handlers:
        root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_root_logger()
    return logging.getLogger(name)
