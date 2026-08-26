from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin

if TYPE_CHECKING:
    from app.models.ai_analysis_result import AIAnalysisResult
    from app.models.patient import Patient
    from app.models.xray_image import XrayImage


class MedicalRecord(TimestampMixin, Base):
    __tablename__ = "medical_records"
    __table_args__ = (
        UniqueConstraint("chart_number", name="uq_medical_records_chart_number"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        comment="환자 정보 ID",
    )
    chart_number: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="환자 진료 차트 번호"
    )
    symptoms: Mapped[str] = mapped_column(
        Text, nullable=False, comment="환자 증상 기록"
    )

    patient: Mapped["Patient"] = relationship(back_populates="medical_records")
    xray_images: Mapped[list["XrayImage"]] = relationship(
        back_populates="medical_record",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    ai_analysis_results: Mapped[list["AIAnalysisResult"]] = relationship(
        back_populates="medical_record",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
