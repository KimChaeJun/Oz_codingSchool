from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base


class XrayImage(Base):
    __tablename__ = "xray_images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    record_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("medical_records.id", ondelete="CASCADE"),
        nullable=False,
    )

    uploader_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    shooting_datetime: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    medical_record: Mapped["MedicalRecord"] = relationship(
        back_populates="xray_images"
    )

    uploader: Mapped["User | None"] = relationship(
        back_populates="uploaded_xray_images"
    )