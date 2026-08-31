from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MedicalRecord


class MedicalRecordRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, record_id: int) -> MedicalRecord | None:
        return await db.get(MedicalRecord, record_id)

    @staticmethod
    async def get_by_id_with_images(
        db: AsyncSession, record_id: int
    ) -> MedicalRecord | None:
        statement = (
            select(MedicalRecord)
            .where(MedicalRecord.id == record_id)
            .options(selectinload(MedicalRecord.xray_images))
        )
        return await db.scalar(statement)

    @staticmethod
    async def get_by_chart_number(
        db: AsyncSession, chart_number: str
    ) -> MedicalRecord | None:
        statement = select(MedicalRecord).where(
            MedicalRecord.chart_number == chart_number
        )
        return await db.scalar(statement)

    @staticmethod
    async def list_by_patient_id(
        db: AsyncSession, patient_id: int
    ) -> list[MedicalRecord]:
        statement = (
            select(MedicalRecord)
            .where(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.created_at.desc())
        )
        result = await db.scalars(statement)
        return list(result.all())
