from enum import Enum
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, UTC
from app.core.db.databases import Base
from app.core.db.models import UUIDMixin, TimestampMixin


class GenderEnum(str, Enum):
    M = "M"
    F = "F"


class RoleEnum(str, Enum):
    PENDING = "PENDING"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class DepartmentEnum(str, Enum):
    MEDICAL = "MEDICAL"
    DEV = "DEV"
    RESEARCH = "RESEARCH"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    gender: Mapped[GenderEnum] = mapped_column(SQLEnum(GenderEnum), nullable=False)
    department: Mapped[DepartmentEnum] = mapped_column(SQLEnum(DepartmentEnum), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(SQLEnum(RoleEnum), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
