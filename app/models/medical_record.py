from sqlalchemy import String, Text, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, UTC
from app.core.db.databases import Base
from app.core.db.models import TimestampMixin


class MedicalRecord(Base, TimestampMixin):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    chart_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)

    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="medical_records",
        foreign_keys=[patient_id],
    )
    xray_images: Mapped[list["XrayImage"]] = relationship(
        "XrayImage",
        back_populates="medical_record",
        cascade="all, delete-orphan",
        foreign_keys="XrayImage.record_id",
    )
    ai_analysis_results: Mapped[list["AiAnalysisResult"]] = relationship(
        "AiAnalysisResult",
        back_populates="medical_record",
        cascade="all, delete-orphan",
        foreign_keys="AiAnalysisResult.record_id",
    )
