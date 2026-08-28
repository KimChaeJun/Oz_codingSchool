from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Gender


class PatientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=30)
    age: int = Field(ge=0, le=150)
    gender: Gender
    phone: str = Field(min_length=11, max_length=11)


class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=30)
    phone: str | None = Field(default=None, min_length=11, max_length=11)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    gender: Gender | None
    phone: str
    created_at: datetime
    updated_at: datetime | None


class PatientListQuery(BaseModel):
    name: str | None = None
    gender: Gender | None = None
    min_age: int | None = Field(default=None, ge=0, le=150)
    max_age: int | None = Field(default=None, ge=0, le=150)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    page: int
    size: int