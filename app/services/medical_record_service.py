import logging
from datetime import UTC, datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import delete_xray_image, save_xray_image
from app.models import MedicalRecord, User, XrayImage
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.patient_repository import PatientRepository

logger = logging.getLogger(__name__)


class MedicalRecordService:
    @staticmethod
    def _cleanup_image(image_url: str) -> None:
        try:
            delete_xray_image(image_url)
        except OSError:
            logger.warning("X-Ray 파일 삭제 실패: %s", image_url, exc_info=True)

    @classmethod
    async def register(
        cls,
        db: AsyncSession,
        *,
        patient_id: int,
        chart_number: str,
        symptoms: str,
        xray_image: UploadFile,
        current_user: User,
    ) -> MedicalRecord:
        patient = await PatientRepository.get_by_id(db, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="환자를 찾을 수 없습니다.",
            )

        if await MedicalRecordRepository.get_by_chart_number(db, chart_number):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 진료 차트 넘버입니다.",
            )

        image_url = await save_xray_image(xray_image)

        try:
            medical_record = MedicalRecord(
                patient_id=patient_id,
                chart_number=chart_number,
                symptoms=symptoms,
            )
            db.add(medical_record)
            await db.flush()

            db.add(
                XrayImage(
                    record_id=medical_record.id,
                    uploader_id=current_user.id,
                    image_url=image_url,
                    shooting_datetime=datetime.now(UTC),
                )
            )
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            cls._cleanup_image(image_url)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 진료 차트 넘버입니다.",
            ) from exc
        except DataError as exc:
            await db.rollback()
            cls._cleanup_image(image_url)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="입력한 내용이 너무 깁니다.",
            ) from exc
        except Exception:
            await db.rollback()
            cls._cleanup_image(image_url)
            raise

        return await MedicalRecordRepository.get_by_id_with_images(
            db, medical_record.id
        )

    @staticmethod
    async def list_by_patient(db: AsyncSession, patient_id: int) -> list[MedicalRecord]:
        patient = await PatientRepository.get_by_id(db, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="환자를 찾을 수 없습니다.",
            )
        return await MedicalRecordRepository.list_by_patient_id(db, patient_id)

    @staticmethod
    async def get_detail(db: AsyncSession, record_id: int) -> MedicalRecord:
        medical_record = await MedicalRecordRepository.get_by_id_with_images(
            db, record_id
        )
        if medical_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료기록을 찾을 수 없습니다.",
            )
        return medical_record
