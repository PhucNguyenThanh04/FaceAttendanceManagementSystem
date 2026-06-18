import uvicorn
from app.core.configs.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.ai_server_host,
        port=settings.ai_service_port,
        reload=False,
        log_level="debug" if settings.debug else "info",
    )