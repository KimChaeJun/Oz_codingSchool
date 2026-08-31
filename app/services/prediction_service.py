from decimal import Decimal

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from PIL import UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import resolve_media_path
from app.models import AiAnalysisResult, MedicalRecord
from app.repositories.ai_analysis_result_repository import AiAnalysisResultRepository
from app.repositories.medical_record_repository import MedicalRecordRepository
from worker.model import MODEL_VERSION, predict


class PredictionService:
    @staticmethod
    async def _require_medical_record(
        db: AsyncSession, record_id: int
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
        cls, db: AsyncSession, record_id: int
    ) -> tuple[AiAnalysisResult, bool]:
        medical_record = await cls._require_medical_record(db, record_id)

        # 동일 record_id + ai_model 조합에 DB-level UniqueConstraint는 없다
        # (현재 alembic history가 multiple heads 상태라 이번 구현 범위에서는
        # migration을 추가하지 않기로 결정함 — docs/6일차_폐렴예측_API_설계.md
        # 4.4, 11장 참고). 아래 조회로 애플리케이션 레벨에서만 중복을 막으며,
        # 동시 요청이 겹치면 중복 행이 생길 수 있는 한계가 남아있다.
        cached_result = await AiAnalysisResultRepository.get_by_record_and_model(
            db, record_id=record_id, ai_model=MODEL_VERSION
        )
        if cached_result is not None:
            return cached_result, True

        if not medical_record.xray_images:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="진료기록에 예측에 사용할 X-Ray 이미지가 없습니다.",
            )

        # 설계 결정: 여러 장이어도 관계에서 반환되는 첫 번째 이미지를 사용한다.
        # XrayImage relationship에는 명시적 order_by가 없어 이는 "업로드
        # 순서 보장"이 아니라 현재 구현의 임시 규칙이다.
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
            prediction = await run_in_threadpool(predict, image_path)
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="유효한 흉부 X-Ray 이미지를 읽을 수 없습니다.",
            ) from exc

        predicted_class_probability = (
            prediction.pneumonia_probability
            if prediction.is_pneumonia
            else 1.0 - prediction.pneumonia_probability
        )
        confidence_percentage = Decimal(f"{predicted_class_probability * 100:.2f}")

        result = AiAnalysisResult(
            record_id=record_id,
            is_pneumonia=prediction.is_pneumonia,
            confidence=confidence_percentage,
            heatmap_url="",
            ai_model=prediction.model_version,
        )
        db.add(result)
        await db.commit()
        await db.refresh(result)
        return result, False

    @classmethod
    async def list_by_record(
        cls, db: AsyncSession, record_id: int
    ) -> list[AiAnalysisResult]:
        await cls._require_medical_record(db, record_id)
        return await AiAnalysisResultRepository.list_by_record_id(db, record_id)
