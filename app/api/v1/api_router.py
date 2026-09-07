# -------------------------------------------------------
# app/api/v1/api_router.py
# Gom tất cả các router của v1
# -------------------------------------------------------
from fastapi import APIRouter
from app.api.v1.endpoints import analyze, health, tasks

api_router = APIRouter()

api_router.include_router(analyze.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(health.router, tags=["health"])