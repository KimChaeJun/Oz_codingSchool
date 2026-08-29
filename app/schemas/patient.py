from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Gender


class XrayImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    image_url: str
    created_at: datetime


class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    age: int = Field(ge=0, le=150)
    gender: Gender
    phone: str = Field(min_length=10, max_length=20)


class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=30)
    phone: str | None = Field(default=None, min_length=10, max_length=20)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    age: int
    gender: Gender | None
    phone: str
    created_at: datetime
    updated_at: datetime | None


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    page: int
    size: int


class MedicalRecordUpdate(BaseModel):
    chart_number: str | None = Field(default=None, min_length=1, max_length=50)
    symptoms: str | None = Field(default=None, min_length=1, max_length=1000)


class MedicalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_images: list[XrayImageResponse]
    created_at: datetime
    updated_at: datetime | None


class MedicalRecordListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    created_at: datetime


class MedicalRecordListItemsResponse(BaseModel):
    items: list[MedicalRecordListItemResponse]
    total: int
