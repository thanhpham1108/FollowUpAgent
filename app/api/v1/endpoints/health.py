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
#
# TODO: Implement health check logic
# -------------------------------------------------------
