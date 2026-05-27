# run.py
import uvicorn
from src.core.configs.settings import settings
if __name__ == "__main__":
    uvicorn.run(
        "src_Antispoofting.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )

