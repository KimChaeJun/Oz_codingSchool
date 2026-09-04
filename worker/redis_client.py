import os

from redis import ConnectionPool, Redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

redis_pool = ConnectionPool.from_url(REDIS_URL, decode_responses=True)


def get_redis() -> Redis:
    return Redis(connection_pool=redis_pool)
