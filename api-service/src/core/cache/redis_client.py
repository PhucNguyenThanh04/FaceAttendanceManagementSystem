

"""
Redis client — dùng cho cooldown chấm công và blacklist refresh token.
"""

import redis.asyncio as aioredis
from src.core.configs.settings import settings

# Global client, khởi tạo một lần khi app start
_redis_client: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


def get_redis() -> aioredis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis chưa được khởi tạo. Gọi init_redis() trước.")
    return _redis_client