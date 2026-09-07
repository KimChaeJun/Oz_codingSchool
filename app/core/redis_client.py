from redis.asyncio import Redis

from app.core.config import settings

REDIS_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"


def get_redis() -> Redis:
    """호출마다 새 연결을 만든다 (요청 단위로 항상 finally에서 aclose됨).

    모듈 레벨 전역 ConnectionPool을 재사용하면, import 시점에 열린
    이벤트 루프에 커넥션이 묶여서 다른 이벤트 루프(예: 테스트마다 루프를
    새로 만드는 pytest-asyncio)에서 재사용 시 "Event loop is closed"가
    발생한다.
    """
    return Redis.from_url(REDIS_URL, decode_responses=True)
