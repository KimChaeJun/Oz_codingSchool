import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import DepartmentEnum, GenderEnum, RoleEnum


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
        if not re.search(r"[A-Z]", value):
            raise ValueError("비밀번호에는 대문자가 1개 이상 포함되어야 합니다.")

        if not re.search(r"[a-z]", value):
            raise ValueError("비밀번호에는 소문자가 1개 이상 포함되어야 합니다.")

        if not re.search(r"\d", value):
            raise ValueError("비밀번호에는 숫자가 1개 이상 포함되어야 합니다.")

        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("비밀번호에는 특수문자가 1개 이상 포함되어야 합니다.")

        return value


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
        if not re.search(r"[A-Z]", value):
            raise ValueError("비밀번호에는 대문자가 1개 이상 포함되어야 합니다.")

        if not re.search(r"[a-z]", value):
            raise ValueError("비밀번호에는 소문자가 1개 이상 포함되어야 합니다.")

        if not re.search(r"\d", value):
            raise ValueError("비밀번호에는 숫자가 1개 이상 포함되어야 합니다.")

        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("비밀번호에는 특수문자가 1개 이상 포함되어야 합니다.")

        return value


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

