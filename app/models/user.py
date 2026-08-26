from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin
from app.models.enums import Department, Gender, UserRole

if TYPE_CHECKING:
    from app.models.xray_image import XrayImage


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("phone_number", name="uq_users_phone_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="해시화된 비밀번호"
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_number: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="유저 휴대폰 번호"
    )
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="gender"), nullable=False, comment="성별"
    )
    department: Mapped[Department] = mapped_column(
        Enum(Department, name="department"), nullable=False, comment="소속 부서"
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="role"), nullable=False, comment="부여된 역할 권한"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        comment="계정 활성화 여부",
    )

    uploaded_xray_images: Mapped[list["XrayImage"]] = relationship(
        back_populates="uploader",
        passive_deletes=True,
    )
