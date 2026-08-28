from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class XrayImageResponse(BaseModel):
    id: int
    image_url: str
    created_at: datetime
    class Config:
        from_attributes = True

class PatientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., regex="^[MF]$")
    phone: str = Field(..., min_length=10, max_length=20)

class PatientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)

class PatientResponse(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    phone: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    page: int
    size: int

class MedicalRecordCreate(BaseModel):
    chart_number: str = Field(..., min_length=1, max_length=100)
    symptoms: str = Field(..., min_length=1, max_length=1000)

class MedicalRecordUpdate(BaseModel):
    chart_number: Optional[str] = Field(None, min_length=1, max_length=100)
    symptoms: Optional[str] = Field(None, min_length=1, max_length=1000)

class MedicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_images: List[XrayImageResponse]
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class MedicalRecordListResponse(BaseModel):
    items: List[MedicalRecordResponse]
    total: int

class MedicalRecordListItemResponse(BaseModel):
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    created_at: datetime
    class Config:
        from_attributes = True

class MedicalRecordListItemsResponse(BaseModel):
    items: List[MedicalRecordListItemResponse]
    total: int
