from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Gender, MedicalRecord, Patient


class PatientRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, patient_id: int) -> Patient | None:
        return await db.get(Patient, patient_id)

    @staticmethod
    async def get_with_full_relations(
        db: AsyncSession, patient_id: int
    ) -> Patient | None:
        statement = (
            select(Patient)
            .where(Patient.id == patient_id)
            .options(
                selectinload(Patient.medical_records).selectinload(
                    MedicalRecord.xray_images
                )
            )
        )
        return await db.scalar(statement)

    @staticmethod
    async def list_patients(
        db: AsyncSession,
        *,
        search: str | None,
        gender: Gender | None,
        age_min: int | None,
        age_max: int | None,
    ) -> list[Patient]:
        filters = []
        if search:
            filters.append(func.lower(Patient.name).like(f"%{search.casefold()}%"))
        if gender:
            filters.append(Patient.gender == gender)
        if age_min is not None:
            filters.append(Patient.age >= age_min)
        if age_max is not None:
            filters.append(Patient.age <= age_max)

        statement = (
            select(Patient).where(*filters).order_by(Patient.created_at.desc())
        )
        result = await db.scalars(statement)
        return list(result.all())
