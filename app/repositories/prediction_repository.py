from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AiAnalysisResult


class PredictionRepository:
    @staticmethod
    async def get_by_record_and_model(
        db: AsyncSession,
        *,
        record_id: int,
        model_version: str,
    ) -> AiAnalysisResult | None:
        statement = select(AiAnalysisResult).where(
            AiAnalysisResult.record_id == record_id,
            AiAnalysisResult.ai_model == model_version,
        )
        return await db.scalar(statement)

    @staticmethod
    async def list_by_record_id(
        db: AsyncSession,
        record_id: int,
    ) -> list[AiAnalysisResult]:
        statement = (
            select(AiAnalysisResult)
            .where(AiAnalysisResult.record_id == record_id)
            .order_by(AiAnalysisResult.created_at.desc(), AiAnalysisResult.id.desc())
        )
        result = await db.scalars(statement)
        return list(result.all())
