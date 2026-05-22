from redis import Redis
from redis.asyncio import Redis as AsyncRedis


def create_sync_redis_client(redis_url: str) -> Redis:
    return Redis.from_url(redis_url, decode_responses=False)


def create_async_redis_client(redis_url: str) -> AsyncRedis:
    return AsyncRedis.from_url(redis_url, decode_responses=False)
