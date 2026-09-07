"""FastAPI 앱과 AI Worker가 함께 참조하는 통신 규약 상수.

app -> worker, worker -> app 어느 쪽도 서로를 import하지 않도록,
두 프로세스가 공유해야 하는 값만 이 모듈에 둔다.
"""

MODEL_VERSION = "resnet18_daycon_pure_v1"

PREDICTION_TASK_QUEUE = "prediction:tasks"
PREDICTION_RESULT_CHANNEL_PREFIX = "prediction:result:"


def prediction_result_channel(task_id: str) -> str:
    return f"{PREDICTION_RESULT_CHANNEL_PREFIX}{task_id}"
