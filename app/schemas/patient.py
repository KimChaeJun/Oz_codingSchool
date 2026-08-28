from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import Gender
from app.schemas.user import PhoneNumber, StrictRequest

PatientName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
]
PatientAge = Annotated[int, Field(ge=0, le=120)]


class PatientCreateRequest(StrictRequest):
    name: PatientName
    age: PatientAge
    gender: Gender
    phone: PhoneNumber


class PatientUpdateRequest(StrictRequest):
    name: PatientName | None = None
    phone: PhoneNumber | None = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    gender: Gender
    phone: str
    created_at: datetime
    updated_at: datetime | None


class PatientDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    gender: Gender
    phone: str
    age: int


class PatientListQuery(StrictRequest):
    search: str | None = Field(default=None, min_length=1, max_length=30)
    gender: Gender | None = None
    age_min: int | None = Field(default=None, ge=0, le=120)
    age_max: int | None = Field(default=None, ge=0, le=120)
