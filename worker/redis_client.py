import os

from redis import Redis


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

PREDICTION_QUEUE = "prediction_queue"
PREDICTION_RESULT_CHANNEL = "prediction_result"


redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_timeout=None,
)