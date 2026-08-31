import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import delete_xray_image
from app.models import Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreateRequest, PatientListQuery, PatientUpdateRequest

logger = logging.getLogger(__name__)


class PatientService:
    @staticmethod
    async def _commit(db: AsyncSession, duplicate_detail: str) -> None:
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=duplicate_detail,
            ) from exc

    @classmethod
    async def register(cls, db: AsyncSession, body: PatientCreateRequest) -> Patient:
        patient = Patient(
            name=body.name,
            age=body.age,
            gender=body.gender,
            phone=body.phone,
        )
        db.add(patient)
        await cls._commit(db, "환자 정보 등록 중 충돌이 발생했습니다.")
        await db.refresh(patient)
        return patient

    @staticmethod
    async def get_patient(db: AsyncSession, patient_id: int) -> Patient:
        patient = await PatientRepository.get_by_id(db, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="환자를 찾을 수 없습니다.",
            )
        return patient

    @staticmethod
    async def list_patients(db: AsyncSession, query: PatientListQuery) -> list[Patient]:
        return await PatientRepository.list_patients(
            db,
            search=query.search,
            gender=query.gender,
            age_min=query.age_min,
            age_max=query.age_max,
        )

    @classmethod
    async def update(
        cls, db: AsyncSession, patient: Patient, body: PatientUpdateRequest
    ) -> Patient:
        updates = body.model_dump(exclude_unset=True, exclude_none=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 항목을 하나 이상 입력해야 합니다.",
            )

        for field, value in updates.items():
            setattr(patient, field, value)
        await cls._commit(db, "환자 정보 수정 중 충돌이 발생했습니다.")
        await db.refresh(patient)
        return patient

    @classmethod
    async def delete(cls, db: AsyncSession, patient_id: int) -> None:
        patient = await PatientRepository.get_with_full_relations(db, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="환자를 찾을 수 없습니다.",
            )

        image_urls = [
            xray_image.image_url
            for medical_record in patient.medical_records
            for xray_image in medical_record.xray_images
        ]

        await db.delete(patient)
        await cls._commit(db, "환자 삭제 중 충돌이 발생했습니다.")

        for image_url in image_urls:
            try:
                delete_xray_image(image_url)
            except OSError:
                logger.warning("X-Ray 파일 삭제 실패: %s", image_url, exc_info=True)
