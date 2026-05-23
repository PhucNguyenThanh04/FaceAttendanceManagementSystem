from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
from sqlalchemy import text
from src.core.cache.redis_client import create_redis_async_client
from src.core.configs.settings import settings
from src.core.db.database import engine
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__, level=logging.DEBUG if settings.debug else logging.INFO)


def parse_cors_origins(raw_origins: str) -> list[str]:
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = None
    ai_http_client = None

    try:
        # Startup
        redis_client = create_redis_async_client()
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis kết nối thành công")

        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        logger.info("PostgreSQL kết nối thành công")

        ai_http_client = httpx.AsyncClient(
            base_url=settings.ai_service_base_url,
            timeout=httpx.Timeout(10.0, connect=3.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        app.state.ai_http = ai_http_client
        logger.info(
            "HTTP client khởi tạo thành công với base URL: %s",
            settings.ai_service_base_url,
        )

        yield
    except Exception:
        logger.exception("Lỗi khởi tạo tài nguyên trong lifespan")
        raise
    finally:
        if ai_http_client is not None:
            await ai_http_client.aclose()
            logger.info("HTTP client đã đóng")
        if redis_client is not None:
            await redis_client.aclose()
            logger.info("Redis client đã đóng")


app = FastAPI(
    title="Face Attendance API",
    description="Hệ thống chấm công nhận diện khuôn mặt",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,   # tắt docs trên production
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Hello, world!"}
