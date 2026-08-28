from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class XrayImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    shooting_datetime: datetime
    created_at: datetime


class MedicalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_images: list[XrayImageResponse]
    created_at: datetime
    updated_at: datetime | None


class MedicalRecordListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    created_at: datetime


class MedicalRecordListResponse(BaseModel):
    items: list[MedicalRecordListItem]
    total: int


class MedicalRecordUpdate(BaseModel):
    symptoms: str | None = Field(default=None, min_length=1)