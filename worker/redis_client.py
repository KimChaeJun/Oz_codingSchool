import os

from redis import ConnectionPool, Redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

redis_pool = ConnectionPool.from_url(
    REDIS_URL,
    decode_responses=True,
    # redis-py는 socket_timeout 기본값을 5초로 두는데, worker/main.py의
    # BRPOP timeout(5초)과 같으면 서버가 nil로 정상 응답하기 전에 클라이언트
    # 소켓이 먼저 타임아웃돼 워커 프로세스가 죽는다. BRPOP timeout 인자가
    # 이미 서버 쪽에서 응답 시간을 보장하므로 클라이언트 소켓은 무제한으로 둔다.
    socket_timeout=None,
)


def get_redis() -> Redis:
    return Redis(connection_pool=redis_pool)
