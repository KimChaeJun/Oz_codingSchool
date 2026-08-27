from sqlalchemy import String, Boolean, BigInteger, ForeignKey, Numeric, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, UTC
from decimal import Decimal
from app.core.db.databases import Base


class AiAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False
    )
    is_pneumonia: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    heatmap_url: Mapped[str] = mapped_column(String(255), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        server_default=text("current_timestamp(0)"),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=lambda: datetime.now(UTC)
    )

    medical_record: Mapped["MedicalRecord"] = relationship(
        "MedicalRecord",
        back_populates="ai_analysis_results",
        foreign_keys=[record_id],
    )
