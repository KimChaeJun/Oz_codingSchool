import json

from worker.model import predict_pneumonia
from worker.redis_client import (
    PREDICTION_QUEUE,
    PREDICTION_RESULT_CHANNEL,
    REDIS_HOST,
    REDIS_PORT,
    redis_client,
)


def process_prediction(task: dict) -> dict:
    prediction = predict_pneumonia(task["image_path"])

    return {
        "task_id": task["task_id"],
        "record_id": task["record_id"],
        "model_name": task["model_name"],
        "image_hash": task["image_hash"],
        "is_pneumonia": prediction["is_pneumonia"],
        "confidence": prediction["confidence"],
        "heatmap_url": "",
    }


def main() -> None:
    print("AI Worker started.")
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")

    while True:
        try:
            task_data = redis_client.brpop(
                PREDICTION_QUEUE,
                timeout=5,
            )

            if task_data is None:
                continue

            _, raw_task = task_data
            task = json.loads(raw_task)

            try:
                result = process_prediction(task)

                redis_client.publish(
                    PREDICTION_RESULT_CHANNEL,
                    json.dumps(result),
                )

                print(
                    "Prediction completed: "
                    f"task_id={result['task_id']}, "
                    f"record_id={result['record_id']}"
                )

            except Exception as exc:
                error_result = {
                    "task_id": task.get("task_id"),
                    "record_id": task.get("record_id"),
                    "model_name": task.get("model_name"),
                    "image_hash": task.get("image_hash"),
                    "error": str(exc),
                }

                redis_client.publish(
                    PREDICTION_RESULT_CHANNEL,
                    json.dumps(error_result),
                )

                print(
                    "Prediction failed: "
                    f"task_id={task.get('task_id')}, "
                    f"error={exc}"
                )

        except Exception as exc:
            print(
                "Redis queue error: "
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()