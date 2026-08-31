from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import resolve_media_path
from app.models import AiAnalysisResult, MedicalRecord
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.prediction_repository import PredictionRepository
from worker.model import (
    MODEL_VERSION,
    InvalidXrayImageError,
    pneumonia_predictor,
)


@dataclass(frozen=True, slots=True)
class PredictionExecution:
    result: AiAnalysisResult
    cached: bool


class PredictionService:
    @staticmethod
    async def _require_medical_record(
        db: AsyncSession,
        record_id: int,
    ) -> MedicalRecord:
        medical_record = await MedicalRecordRepository.get_by_id_with_images(
            db, record_id
        )
        if medical_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료기록을 찾을 수 없습니다.",
            )
        return medical_record

    @classmethod
    async def predict(
        cls,
        db: AsyncSession,
        record_id: int,
    ) -> PredictionExecution:
        medical_record = await cls._require_medical_record(db, record_id)

        cached_result = await PredictionRepository.get_by_record_and_model(
            db,
            record_id=record_id,
            model_version=MODEL_VERSION,
        )
        if cached_result is not None:
            return PredictionExecution(result=cached_result, cached=True)

        if not medical_record.xray_images:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="진료기록에 예측에 사용할 X-Ray 이미지가 없습니다.",
            )

        try:
            image_path = resolve_media_path(medical_record.xray_images[0].image_url)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="저장된 X-Ray 이미지 경로가 유효하지 않습니다.",
            ) from exc

        if not image_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="저장된 X-Ray 이미지 파일을 찾을 수 없습니다.",
            )

        try:
            prediction = await run_in_threadpool(
                pneumonia_predictor.predict,
                image_path,
            )
        except InvalidXrayImageError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

        result = AiAnalysisResult(
            record_id=record_id,
            is_pneumonia=prediction.is_pneumonia,
            confidence=Decimal(f"{prediction.confidence:.2f}"),
            # Heatmap generation is optional in REQ-PRED-001. The existing
            # schema is NOT NULL, so an empty value is stored and exposed as null.
            heatmap_url="",
            ai_model=prediction.model_version,
        )
        db.add(result)

        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            # Another worker may have inserted the same record/model result
            # while this process was running inference. Reuse that row.
            concurrent_result = await PredictionRepository.get_by_record_and_model(
                db,
                record_id=record_id,
                model_version=MODEL_VERSION,
            )
            if concurrent_result is not None:
                return PredictionExecution(result=concurrent_result, cached=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="폐렴 예측 결과 저장 중 충돌이 발생했습니다.",
            ) from exc
        except Exception:
            await db.rollback()
            raise

        await db.refresh(result)
        return PredictionExecution(result=result, cached=False)

    @classmethod
    async def list_by_record(
        cls,
        db: AsyncSession,
        record_id: int,
    ) -> list[AiAnalysisResult]:
        await cls._require_medical_record(db, record_id)
        return await PredictionRepository.list_by_record_id(db, record_id)
