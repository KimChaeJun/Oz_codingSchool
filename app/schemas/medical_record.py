from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

SYMPTOMS_PREVIEW_LIMIT = 100

# MySQL TEXT 컬럼의 실제 물리적 한계(문자셋과 무관하게 65,535바이트 고정).
# 문자 수가 아니라 UTF-8 인코딩 바이트 기준으로 검증해야 한다(한글은 3바이트).
SYMPTOMS_MAX_BYTES = 65535


def validate_symptoms_byte_length(value: str) -> str:
    if len(value.encode("utf-8")) > SYMPTOMS_MAX_BYTES:
        raise ValueError("증상 내용이 너무 깁니다.")
    return value


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
    patient_id: int
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
