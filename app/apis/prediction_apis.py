import asyncio
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.apis.dependencies import CurrentUser, DatabaseSession
from app.core.redis_client import redis_client
from app.models import AiAnalysisResult, Department, MedicalRecord
from app.schemas.prediction import PredictionResponse


router = APIRouter(
    prefix="/api/v1/medical-records/{record_id}/prediction",
    tags=["prediction"],
)

ALLOWED_DEPARTMENTS = {
    Department.MEDICAL,
    Department.DEV,
    Department.RESEARCH,
}

MODEL_NAME = "SimpleCNN"

PREDICTION_QUEUE = "prediction_queue"
PREDICTION_RESULT_CHANNEL = "prediction_result"

RESULT_TIMEOUT_SECONDS = 60


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def check_role(current_user: CurrentUser) -> None:
    if current_user.department not in ALLOWED_DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="폐렴 예측 API를 사용할 권한이 없습니다.",
        )


async def get_record(
    record_id: int,
    db: DatabaseSession,
) -> MedicalRecord:
    result = await db.execute(
        select(MedicalRecord)
        .options(selectinload(MedicalRecord.xray_images))
        .where(MedicalRecord.id == record_id)
    )

    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="진료기록을 찾을 수 없습니다.",
        )

    return record


async def get_image_path_and_hash(
    record: MedicalRecord,
    xray_image: UploadFile | None,
) -> tuple[Path, str]:
    if xray_image is not None:
        if (
            not xray_image.content_type
            or not xray_image.content_type.startswith("image/")
        ):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="이미지 파일만 업로드할 수 있습니다.",
            )

        image_bytes = await xray_image.read()

        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="빈 이미지 파일은 업로드할 수 없습니다.",
            )

        image_hash = hashlib.sha256(image_bytes).hexdigest()

        image_dir = project_root() / "media" / "xray"
        image_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(xray_image.filename or "").suffix.lower()

        if not suffix:
            suffix = ".jpg"

        image_path = image_dir / f"{image_hash}{suffix}"

        if not image_path.exists():
            image_path.write_bytes(image_bytes)

        return image_path, image_hash

    if record.xray_images:
        image_path = (
            project_root()
            / record.xray_images[0].image_url.lstrip("/")
        )

        if not image_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="X-Ray 이미지 파일을 찾을 수 없습니다.",
            )

        image_bytes = image_path.read_bytes()
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        return image_path, image_hash

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="진료기록에 연결된 X-Ray 이미지가 없습니다.",
    )


async def wait_for_prediction_result(
    pubsub,
    task_id: str,
) -> dict:
    try:
        async with asyncio.timeout(RESULT_TIMEOUT_SECONDS):
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                result = json.loads(message["data"])

                if result.get("task_id") != task_id:
                    continue

                return result

    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 예측 처리 시간이 초과되었습니다.",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="AI 예측 결과를 받을 수 없습니다.",
    )


@router.post(
    "",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="폐렴 예측 결과 생성",
)
async def create_prediction(
    record_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
    xray_image: UploadFile | None = File(default=None),
):
    check_role(current_user)

    record = await get_record(record_id, db)

    image_path, image_hash = await get_image_path_and_hash(
        record,
        xray_image,
    )

    # 같은 진료기록 + 같은 이미지 + 같은 AI 모델의
    # 기존 결과가 있는지 먼저 확인한다.
    existing = await db.scalar(
        select(AiAnalysisResult)
        .where(
            AiAnalysisResult.record_id == record_id,
            AiAnalysisResult.ai_model == MODEL_NAME,
            AiAnalysisResult.image_hash == image_hash,
        )
        .order_by(AiAnalysisResult.id.desc())
    )

    if existing is not None:
        return existing

    task_id = str(uuid4())

    # 동일한 이미지와 모델에 대한 중복 작업을 방지한다.
    dedup_key = (
        f"prediction:task:"
        f"{record_id}:"
        f"{MODEL_NAME}:"
        f"{image_hash}"
    )

    existing_task_id = await redis_client.get(dedup_key)

    if existing_task_id:
        task_id = existing_task_id
    else:
        task_created = await redis_client.set(
            dedup_key,
            task_id,
            nx=True,
            ex=RESULT_TIMEOUT_SECONDS + 30,
        )

        if not task_created:
            existing_task_id = await redis_client.get(dedup_key)

            if existing_task_id:
                task_id = existing_task_id

    pubsub = redis_client.pubsub()

    try:
        await pubsub.subscribe(PREDICTION_RESULT_CHANNEL)

        # 내가 생성한 task라면 Queue에 등록한다.
        current_task = await redis_client.get(dedup_key)

        if current_task == task_id:
            queue_task = {
                "task_id": task_id,
                "record_id": record_id,
                "model_name": MODEL_NAME,
                "image_path": str(image_path),
                "image_hash": image_hash,
            }

            # 이미 같은 task가 Queue에 들어갔는지 확인하기 위한
            # 별도의 enqueue key
            enqueue_key = f"prediction:enqueued:{task_id}"

            enqueued = await redis_client.set(
                enqueue_key,
                "1",
                nx=True,
                ex=RESULT_TIMEOUT_SECONDS + 30,
            )

            if enqueued:
                await redis_client.rpush(
                    PREDICTION_QUEUE,
                    json.dumps(queue_task),
                )

        result = await wait_for_prediction_result(
            pubsub,
            task_id,
        )

        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="폐렴 예측 처리 중 오류가 발생했습니다.",
            )

        # Worker가 보낸 결과를 DB에 저장한다.
        analysis = await db.scalar(
            select(AiAnalysisResult).where(
                AiAnalysisResult.record_id == record_id,
                AiAnalysisResult.ai_model == MODEL_NAME,
                AiAnalysisResult.image_hash == image_hash,
            )
        )

        if analysis is not None:
            return analysis

        analysis = AiAnalysisResult(
            record_id=record_id,
            image_hash=image_hash,
            is_pneumonia=result["is_pneumonia"],
            confidence=result["confidence"],
            heatmap_url=result.get("heatmap_url", ""),
            ai_model=MODEL_NAME,
        )

        db.add(analysis)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()

            analysis = await db.scalar(
                select(AiAnalysisResult).where(
                    AiAnalysisResult.record_id == record_id,
                    AiAnalysisResult.ai_model == MODEL_NAME,
                    AiAnalysisResult.image_hash == image_hash,
                )
            )

            if analysis is None:
                raise

            return analysis

        await db.refresh(analysis)

        return analysis

    finally:
        await pubsub.unsubscribe(PREDICTION_RESULT_CHANNEL)
        await pubsub.aclose()


@router.get(
    "",
    response_model=PredictionResponse,
    summary="폐렴 예측 결과 조회",
)
async def get_prediction(
    record_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
):
    check_role(current_user)

    await get_record(record_id, db)

    result = await db.scalar(
        select(AiAnalysisResult)
        .where(
            AiAnalysisResult.record_id == record_id,
            AiAnalysisResult.ai_model == MODEL_NAME,
        )
        .order_by(AiAnalysisResult.id.desc())
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="예측 결과를 찾을 수 없습니다.",
        )

    return result