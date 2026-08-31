from datetime import datetime
from decimal import Decimal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medical_record_id: int = Field(
        validation_alias=AliasChoices("medical_record_id", "record_id")
    )
    is_pneumonia: bool
    confidence: Decimal
    heatmap_url: str | None
    predicted_at: datetime = Field(
        validation_alias=AliasChoices("predicted_at", "created_at")
    )
    model_name: str = Field(
        validation_alias=AliasChoices("model_name", "ai_model")
    )
