from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Engine bất đồng bộ — không cần check_same_thread (chỉ là tham số của SQLite)
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Session factory bất đồng bộ
SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency injection để lấy async DB session."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
