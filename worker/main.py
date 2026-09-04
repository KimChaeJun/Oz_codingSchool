"""AI 예측 Worker 진입점.

Redis Task Queue(prediction:tasks)에서 작업을 꺼내(BRPOP) 폐렴 예측을 수행하고,
결과를 요청별 Pub/Sub 채널로 Publish한다. BRPOP은 원자적이라 이 스크립트를
여러 프로세스로 동시에 띄워도(다중 워커) 같은 작업이 중복 소비되지 않는다.
"""

import json
import logging
from pathlib import Path

from PIL import UnidentifiedImageError
from redis import Redis

from shared.constants import PREDICTION_TASK_QUEUE, prediction_result_channel
from worker import model as worker_model
from worker.redis_client import get_redis

logger = logging.getLogger(__name__)

MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media"

# BRPOP 대기 시간(초). 워커가 완전히 멈춰있지 않고 주기적으로 깨어나게 함.
POLL_TIMEOUT_SECONDS = 5


def resolve_image_path(image_url: str) -> Path:
    """FastAPI가 보낸 공개 media URL을 Worker 로컬 파일 경로로 변환한다.

    app/core/storage.py의 동일 검증 로직을 그대로 복제함 — worker가
    app 패키지(및 그 fastapi 의존성)를 import하지 않도록 하기 위한
    의도적인 중복.
    """
    if not image_url.startswith("/media/"):
        raise ValueError(f"지원하지 않는 media 경로입니다: {image_url}")

    media_root = MEDIA_ROOT.resolve()
    relative_path = image_url.removeprefix("/media/")
    file_path = (media_root / relative_path).resolve()

    if not file_path.is_relative_to(media_root):
        raise ValueError(f"media 저장소 범위를 벗어난 경로입니다: {image_url}")

    return file_path


def handle_task(redis: Redis, raw_task: str) -> None:
    task = json.loads(raw_task)
    task_id = task["task_id"]
    channel = prediction_result_channel(task_id)

    try:
        image_path = resolve_image_path(task["image_path"])
        prediction = worker_model.predict(image_path)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        # FastAPI 쪽(prediction_service.py)이 "error" 키를 보고 422로 응답한다.
        redis.publish(
            channel, json.dumps({"task_id": task_id, "error": "invalid_image"})
        )
        logger.warning("이미지 처리 실패: task_id=%s, %s", task_id, exc)
        return

    result = {
        "task_id": task_id,
        "is_pneumonia": prediction.is_pneumonia,
        "pneumonia_probability": prediction.pneumonia_probability,
        "ai_model": prediction.model_version,
    }
    redis.publish(channel, json.dumps(result))
    logger.info("작업 처리 완료: task_id=%s", task_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    redis = get_redis()
    logger.info("AI worker 시작. 큐: %s", PREDICTION_TASK_QUEUE)

    while True:
        try:
            item = redis.brpop(PREDICTION_TASK_QUEUE, timeout=POLL_TIMEOUT_SECONDS)
        except Exception:
            # Redis 연결 문제 등으로 BRPOP 자체가 실패해도 워커 프로세스는
            # 죽지 않고 재시도한다 (예: 컨테이너 시작 순서상 일시적 연결 실패).
            logger.exception("BRPOP 실패, 재시도합니다")
            continue

        if item is None:
            continue

        _, raw_task = item
        try:
            handle_task(redis, raw_task)
        except Exception:
            logger.exception("작업 처리 중 오류 발생: %s", raw_task)


if __name__ == "__main__":
    main()
