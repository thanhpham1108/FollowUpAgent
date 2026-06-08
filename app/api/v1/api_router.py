# -------------------------------------------------------
# app/api/v1/api_router.py
# Gom tất cả các router của v1
# -------------------------------------------------------
from fastapi import APIRouter
from app.api.v1.endpoints import analyze

api_router = APIRouter()

api_router.include_router(analyze.router, prefix="/candidates", tags=["candidates"])
# TODO: Include health router when it's implemented
# api_router.include_router(health.router, tags=["health"])
