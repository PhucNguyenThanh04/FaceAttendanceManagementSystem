import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import AsyncQdrantClient
from app.core.clients.api_server import ApiServerClient
from app.core.vector_db.qdrant_repo import Vectordb
from app.core.configs.settings import settings
from app.core.pipeline.pipe_processor import PipelineProcessor
from app.core.pipeline.attendance_pipline import AttendancePipeline
from app.api.v1.features.register.service import RegisterService


from app.api.v1.router import api_router

from app.utils.setup_logger import setup_logger


logger = setup_logger(__name__)


def _load_pipeline() -> PipelineProcessor:
    logger.info("Loading ML models (device=%s)...", settings.ml_device)
    return PipelineProcessor(
        weight_detector=settings.weight_detector,
        weight_embedder=settings.weight_embedder,
        model_dir_antispoof=settings.model_dir_antispoof,
        device=settings.ml_device,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):

    # 1. Thread pool — giới hạn 2 worker vì ML inference serialize qua Lock
    #    max_workers=2: 1 đang chạy inference, 1 chờ lock — đủ dùng
    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ml_worker")
    loop = asyncio.get_running_loop()
    loop.set_default_executor(executor)
    logger.info("ThreadPoolExecutor started (max_workers=2)")

    # 2. Load ML models trong thread — không block event loop
    pipeline: PipelineProcessor = await asyncio.to_thread(_load_pipeline)
    logger.info("ML models loaded")
    await asyncio.to_thread(pipeline.warmup, 2)
    logger.info("ML pipeline warmed up")

    # 3. Qdrant async client
    qdrant = AsyncQdrantClient(
        host=settings.host_qdrant,
        port=settings.port_qdrant
    )
    try:
        await qdrant.get_collections()
        logger.info("Qdrant connected: %s:%s", settings.host_qdrant, settings.port_qdrant)
    except Exception as e:
        logger.error("Qdrant connection failed: %s", e)
        raise

    vectordb = Vectordb(_client=qdrant, _collection_name=settings.qdrant_collection_name)
    await vectordb.create_collection()
    logger.info("Vectordb ready (collection=%s)", settings.qdrant_collection_name)

    register_service = RegisterService(pipeline=pipeline, vectordb=vectordb)
    api_server_http_client = httpx.AsyncClient(
        base_url=settings.api_server_base_url.rstrip("/"),
        timeout=httpx.Timeout(5.0, connect=3.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    api_server_client = ApiServerClient(api_server_http_client)
    attendance_worker = AttendancePipeline(
        pipline=pipeline,
        vectordb=vectordb,
        camera_url=settings.stream_url,
        loop=loop,
        api_client=api_server_client,
    )


    # 4. Services — pipeline truyền vào service, không expose ra app.state
    app.state.qdrant = qdrant   # health check cần dùng trực tiếp
    app.state.register_service = register_service
    app.state.attendance_worker = attendance_worker
    app.state.api_server_http = api_server_http_client
    app.state.api_server_client = api_server_client

    if settings.attendance_enabled:
        attendance_worker.start()
    else:
        logger.info("Attendance worker disabled")

    logger.info("AI server ready")

    yield   # ← app đang chạy, nhận request

    # ── Shutdown — thứ tự quan trọng ─────────────────────────────────────────
    logger.info("Shutting down AI server...")

    # 1. Dừng worker trước — tránh worker gọi pipeline trong khi executor đóng
    await attendance_worker.stop()
    await api_server_http_client.aclose()
    logger.info("api-service HTTP client closed")

    # 2. Chờ các ML thread đang chạy hoàn thành — tránh kill giữa chừng
    executor.shutdown(wait=True)
    logger.info("ThreadPoolExecutor shutdown")

    # 3. Đóng Qdrant
    await qdrant.close()
    logger.info("Qdrant disconnected")

    logger.info("AI server stopped")


app = FastAPI(
    title="AI Server",
    description="Face recognition pipeline — internal API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root():
    return {"message": "hello world"}

@app.get("/health", tags=["system"])
async def health_check():
    try:
        await app.state.qdrant.get_collections()
    except Exception as e:
        logger.error("Health check failed: Qdrant error: %s", e)
        return {"status": "error", "detail": "Qdrant connection failed"}

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.ai_server_host,
        port=settings.ai_service_port,
        reload=False,
    )
