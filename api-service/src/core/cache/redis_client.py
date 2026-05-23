import redis.asyncio as aioredis
from src.core.configs.settings import settings


def create_redis_async_client() -> aioredis.Redis:
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
