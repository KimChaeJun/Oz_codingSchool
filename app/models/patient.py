from sqlalchemy import String, SmallInteger, Enum as SQLEnum, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, UTC
from enum import Enum
from app.core.db.databases import Base
from app.core.db.models import TimestampMixin


class GenderEnum(str, Enum):
    M = "M"
    F = "F"


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[GenderEnum | None] = mapped_column(SQLEnum(GenderEnum), nullable=True)
    phone: Mapped[str] = mapped_column(String(11), nullable=False)

    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        "MedicalRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
        foreign_keys="MedicalRecord.patient_id",
    )
