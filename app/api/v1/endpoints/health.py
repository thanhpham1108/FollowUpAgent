# -------------------------------------------------------
# app/api/v1/endpoints/health.py
# API kiểm tra trạng thái server & model LLM
# -------------------------------------------------------
# Endpoint: GET /health
#
# Returns:
#   - status: "ok" | "degraded"
#   - uptime_seconds: float
#   - llm_ready: bool (model loaded & responsive?)
# -------------------------------------------------------
import time
import logging
from fastapi import APIRouter
from app.schemas.response import HealthResponse
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Thời điểm server khởi động, dùng để tính uptime
_START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Kiểm tra trạng thái tổng thể của service:
      - Server có đang chạy không (luôn true nếu endpoint trả lời được)
      - LLM model (GGUF) đã được load vào bộ nhớ hay chưa
    """
    uptime_seconds = time.time() - _START_TIME

    # is_ready() là hàm đồng bộ, chỉ kiểm tra self._model is not None
    llm_ready = llm_service.is_ready()

    overall_status = "ok" if llm_ready else "degraded"

    return HealthResponse(
        status=overall_status,
        uptime_seconds=round(uptime_seconds, 2),
        llm_ready=llm_ready
    )