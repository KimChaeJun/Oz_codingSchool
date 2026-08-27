from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Department, Gender, Role


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str
    department: Department
    gender: Gender
    phone_number: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    department: Department
    gender: Gender
    phone_number: str
    role: Role
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    department: Department | None = None
    phone_number: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class RoleUpdate(BaseModel):
    role: Role

class UserStatusUpdate(BaseModel):
    is_active: bool