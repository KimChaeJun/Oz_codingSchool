from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin
from app.models.enums import Gender

if TYPE_CHECKING:
    from app.models.medical_record import MedicalRecord


class Patient(TimestampMixin, Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="환자 성명"
    )
    age: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="환자 나이"
    )
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, name="gender"), nullable=True, comment="환자 성별"
    )
    phone: Mapped[str] = mapped_column(
        String(11), nullable=False, comment="국내 전화번호"
    )

    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
