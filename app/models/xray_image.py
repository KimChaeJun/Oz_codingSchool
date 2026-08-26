from sqlalchemy import String, DateTime, BigInteger, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, UTC
from app.core.db.databases import Base


class XrayImage(Base):
    __tablename__ = "xray_images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False
    )
    uploader_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    shooting_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        server_default=text("current_timestamp(0)"),
        nullable=False,
    )

    medical_record: Mapped["MedicalRecord"] = relationship(
        "MedicalRecord",
        back_populates="xray_images",
        foreign_keys=[record_id],
    )
    uploader: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[uploader_id],
    )
