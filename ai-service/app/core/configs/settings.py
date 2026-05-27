from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# root ai-service
BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):

    api_server_base_url: str

    ai_server_name: str
    ai_server_host: str
    ai_service_port: int
    workers: int
    gpu_id: int
    api_key: str

    log_level: str = "INFO"

    stream_url: str
    host_camera: str
    port_camera: int

    qdrant_collection_name: str
    host_qdrant: str
    port_qdrant: int
    url_qdrant: str
    qdrant_timeout: float = 5.0

    weight_detector: str
    weight_embedder: str
    model_dir_antispoof: str
    ml_device: int

    attendance_cooldown_seconds: int
    attendance_recognized_pause_seconds: float
    attendance_recognition_result_max_age_seconds: float
    attendance_process_fps: float
    attendance_buffer_flush_grabs: int

    required_images: int
    session_timeout: int
    rate_limit_per_minute: int

    # pydantic settings
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()

    
# shortcut toàn app
settings = get_settings()

# helper resolve path tương đối BASE_DIR
settings.weight_detector = (BASE_DIR / settings.weight_detector).resolve()
settings.weight_embedder = (BASE_DIR / settings.weight_embedder).resolve()
settings.model_dir_antispoof = (BASE_DIR / settings.model_dir_antispoof).resolve()