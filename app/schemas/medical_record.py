from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

SYMPTOMS_PREVIEW_LIMIT = 100


class MedicalRecordListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chart_number: str
    symptoms: str
    created_at: datetime

    @field_validator("symptoms")
    @classmethod
    def truncate_symptoms(cls, value: str) -> str:
        if len(value) > SYMPTOMS_PREVIEW_LIMIT:
            return value[:SYMPTOMS_PREVIEW_LIMIT] + "…"
        return value


class MedicalRecordDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chart_number: str
    symptoms: str
    created_at: datetime
    xray_images: list[str]

    @field_validator("xray_images", mode="before")
    @classmethod
    def extract_image_urls(cls, value: object) -> list[str]:
        if value and hasattr(value[0], "image_url"):
            return [image.image_url for image in value]
        return list(value) if value else []
