import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base

if TYPE_CHECKING:
    from app.models.xray_image import XrayImage


class Gender(str, enum.Enum):
    M = "M"
    F = "F"


class Role(str, enum.Enum):
    PENDING = "PENDING"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class Department(str, enum.Enum):
    MEDICAL = "MEDICAL"
    DEV = "DEV"
    RESEARCH = "RESEARCH"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    gender: Mapped[Gender] = mapped_column(Enum(Gender, name="gender"), nullable=False)
    department: Mapped[Department] = mapped_column(
        Enum(Department, name="department"), nullable=False
    )
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role"),
        nullable=False,
        default=Role.PENDING,
        server_default=Role.PENDING.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=func.now()
    )

    uploaded_xray_images: Mapped[list["XrayImage"]] = relationship(
        back_populates="uploader", passive_deletes=True
    )
