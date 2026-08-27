# -------------------------------------------------------
# app/main.py
# Entry point: Khởi tạo FastAPI app, mount routers
# -------------------------------------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api_router import api_router
from app.core import models
from app.core.database import engine, Base
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.services.llm_service import llm_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="FollowUpAgent API",
    description="API for processing candidate audio via background tasks.",
    version="1.0.0"
)

register_exception_handlers(app)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Khởi động FollowUpAgent API (env={settings.APP_ENV})...")

    # Tạo bảng DB qua async engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Đã đảm bảo database tables tồn tại.")

    llm_service.load_model()

    if not llm_service.is_ready():
        logger.warning(
            "LLM model CHƯA sẵn sàng sau khi startup (kiểm tra LLM_MODEL_PATH trong .env). "
            "Endpoint /health sẽ trả về status=degraded cho tới khi model được load."
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Welcome to FollowUpAgent API"}