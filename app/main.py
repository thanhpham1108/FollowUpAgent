# -------------------------------------------------------
# app/main.py
# Entry point: Khởi tạo FastAPI app, mount routers
# -------------------------------------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api_router import api_router
from app.core import models
from app.core.database import engine, Base
from app.services.llm_service import llm_service

app = FastAPI(
    title="FollowUpAgent API",
    description="API for processing candidate audio via background tasks.",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    # Khởi tạo database tables nếu chưa tồn tại
    Base.metadata.create_all(bind=engine)
    # Tải mô hình GGUF cục bộ vào bộ nhớ
    llm_service.load_model()


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to FollowUpAgent API"}
