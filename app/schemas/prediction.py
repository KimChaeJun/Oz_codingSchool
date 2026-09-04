from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    record_id: int
    is_pneumonia: bool
    confidence: float
    heatmap_url: str | None
    predicted_at: datetime = Field(validation_alias="created_at")
    model: str = Field(validation_alias="ai_model")

    @field_validator("heatmap_url", mode="before")
    @classmethod
    def empty_heatmap_as_none(cls, value: object) -> object:
        return None if value == "" else value
