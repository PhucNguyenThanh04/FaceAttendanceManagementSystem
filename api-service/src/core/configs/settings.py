from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]  # đi lên api-service/


class Setting(BaseSettings):
    app_name: str = "API Service"
    debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    ai_service_base_url: str

    database_url: str
    database_port: int
    database_host: str
    database_name: str
    database_user: str
    database_password: str

    redis_host: str
    redis_port: int
    redis_password: str
    redis_url: str
    redis_db_session: int
    redis_db_attendance: int

    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int
    mail_server: str
    mail_tls: bool
    mail_ssl: bool

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    cors_origins: str


    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Setting:
    return Setting()


# Shortcut dùng trong toàn app
settings = get_settings()
