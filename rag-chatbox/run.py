import uvicorn
from src.core.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=8081,
        reload=False,
        log_level="debug" if settings.api_debug else "info",
    )