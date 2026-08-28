import re
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
)

from app.models import Department, Gender, Role

PASSWORD_UPPER_PATTERN = re.compile(r"[A-Z]")
PASSWORD_LOWER_PATTERN = re.compile(r"[a-z]")
PASSWORD_DIGIT_PATTERN = re.compile(r"\d")
PASSWORD_SPECIAL_PATTERN = re.compile(r"[^A-Za-z0-9\s]")
PHONE_PATTERN = re.compile(r"^010\d{8}$")


def normalize_email(value: EmailStr) -> str:
    return str(value).strip().casefold()


def normalize_phone_number(value: str) -> str:
    normalized = re.sub(r"[-\s]", "", value)
    if not PHONE_PATTERN.fullmatch(normalized):
        raise ValueError("휴대폰 번호는 010으로 시작하는 숫자 11자리여야 합니다.")
    return normalized


def validate_password(value: SecretStr) -> SecretStr:
    plain_password = value.get_secret_value()
    if not 8 <= len(plain_password) <= 64:
        raise ValueError("비밀번호는 8자 이상 64자 이하여야 합니다.")
    if not PASSWORD_UPPER_PATTERN.search(plain_password):
        raise ValueError("비밀번호에는 영문 대문자가 1개 이상 필요합니다.")
    if not PASSWORD_LOWER_PATTERN.search(plain_password):
        raise ValueError("비밀번호에는 영문 소문자가 1개 이상 필요합니다.")
    if not PASSWORD_DIGIT_PATTERN.search(plain_password):
        raise ValueError("비밀번호에는 숫자가 1개 이상 필요합니다.")
    if not PASSWORD_SPECIAL_PATTERN.search(plain_password):
        raise ValueError("비밀번호에는 특수문자가 1개 이상 필요합니다.")
    return value


EmailAddress = Annotated[EmailStr, AfterValidator(normalize_email)]
Password = Annotated[
    SecretStr,
    Field(min_length=8, max_length=64),
    AfterValidator(validate_password),
]
RawPassword = Annotated[SecretStr, Field(min_length=1, max_length=64)]
Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=20),
]
PhoneNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=11, max_length=13),
    AfterValidator(normalize_phone_number),
]
PositiveUserId = Annotated[int, Field(gt=0)]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserSignupRequest(StrictRequest):
    email: EmailAddress
    password: Password
    name: Name
    department: Department
    gender: Gender
    phone_number: PhoneNumber


class UserLoginRequest(StrictRequest):
    email: EmailAddress
    password: RawPassword


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    department: Department
    gender: Gender
    phone_number: str
    role: Role
    is_active: bool
    created_at: datetime


class UserListQuery(StrictRequest):
    search: str | None = Field(default=None, min_length=1, max_length=100)
    department: Department | None = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @field_validator("search")
    @classmethod
    def strip_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("검색어는 공백만 입력할 수 없습니다.")
        return stripped


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int


class RoleBulkUpdateRequest(StrictRequest):
    user_ids: list[PositiveUserId] = Field(min_length=1, max_length=100)
    role: Role

    @field_validator("user_ids")
    @classmethod
    def validate_unique_user_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("회원 ID는 중복될 수 없습니다.")
        return value


class RoleBulkUpdateResponse(BaseModel):
    updated_count: int
    role: Role


class UserProfileUpdateRequest(StrictRequest):
    department: Department | None = None
    phone_number: PhoneNumber | None = None


class PasswordChangeRequest(StrictRequest):
    current_password: RawPassword
    new_password: Password
