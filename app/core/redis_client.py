from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

REDIS_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

redis_pool = ConnectionPool.from_url(REDIS_URL, decode_responses=True)


def get_redis() -> Redis:
    return Redis(connection_pool=redis_pool)
