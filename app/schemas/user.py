import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import DepartmentEnum, GenderEnum, RoleEnum

PHONE_NUMBER_PATTERN = re.compile(r"^010-\d{4}-\d{4}$")


def _validate_password_strength(value: str) -> str:
    if not re.search(r"[A-Z]", value):
        raise ValueError("비밀번호에는 대문자가 1개 이상 포함되어야 합니다.")

    if not re.search(r"[a-z]", value):
        raise ValueError("비밀번호에는 소문자가 1개 이상 포함되어야 합니다.")

    if not re.search(r"\d", value):
        raise ValueError("비밀번호에는 숫자가 1개 이상 포함되어야 합니다.")

    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("비밀번호에는 특수문자가 1개 이상 포함되어야 합니다.")

    return value


def _validate_phone_number_format(value: str) -> str:
    if not PHONE_NUMBER_PATTERN.fullmatch(value):
        raise ValueError("휴대폰 번호는 010-0000-0000 형식이어야 합니다.")
    return value


class UserCreateRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=20)
    department: DepartmentEnum
    gender: GenderEnum
    phone_number: str = Field(max_length=20)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("올바른 이메일 형식이 아닙니다.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        return _validate_phone_number_format(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    department: DepartmentEnum
    gender: GenderEnum
    phone_number: str
    role: RoleEnum
    is_active: bool


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    department: DepartmentEnum
    gender: GenderEnum
    phone_number: str
    role: RoleEnum


class UserUpdateRequest(BaseModel):
    department: DepartmentEnum | None = None
    phone_number: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_phone_number_format(value)


class UserUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    email: str
    department: DepartmentEnum
    gender: GenderEnum
    phone_number: str
    role: RoleEnum


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class LoginRequest(BaseModel):
     email: str
     password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str | None = None


class RoleChangeRequest(BaseModel):
    role: RoleEnum


class RoleChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: RoleEnum

