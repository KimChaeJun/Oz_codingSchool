from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.apis.dependencies import CurrentUser, DatabaseSession
from app.models import AiAnalysisResult, Department, MedicalRecord
from app.schemas.prediction import PredictionResponse
from worker.model import predict_pneumonia


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


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


async def get_record(record_id: int, db: DatabaseSession) -> MedicalRecord:
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


def check_role(current_user: CurrentUser) -> None:
    if current_user.department not in ALLOWED_DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="폐렴 예측 API를 사용할 권한이 없습니다.",
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
    xray_image: Annotated[UploadFile | None, File()] = None,
):
    check_role(current_user)
    record = await get_record(record_id, db)

    existing = await db.scalar(
        select(AiAnalysisResult)
        .where(
            AiAnalysisResult.record_id == record_id,
            AiAnalysisResult.ai_model == MODEL_NAME,
        )
        .order_by(AiAnalysisResult.id.desc())
    )
    if existing is not None:
        return existing

    if xray_image is not None:
        if not xray_image.content_type or not xray_image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="이미지 파일만 업로드할 수 있습니다.",
            )
        image_dir = project_root() / "media" / "xray"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / (xray_image.filename or "prediction-image")
        image_path.write_bytes(await xray_image.read())
    elif record.xray_images:
        image_path = project_root() / record.xray_images[0].image_url.lstrip("/")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="진료기록에 연결된 X-Ray 이미지가 없습니다.",
        )

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X-Ray 이미지 파일을 찾을 수 없습니다.",
        )

    try:
        prediction = predict_pneumonia(str(image_path))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="폐렴 예측 처리 중 오류가 발생했습니다.",
        ) from exc

    analysis = AiAnalysisResult(
        record_id=record_id,
        is_pneumonia=prediction["is_pneumonia"],
        confidence=prediction["confidence"],
        heatmap_url="",
        ai_model=MODEL_NAME,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    return analysis


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
