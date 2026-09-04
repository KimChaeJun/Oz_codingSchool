from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AiAnalysisResult


class AiAnalysisResultRepository:
    @staticmethod
    async def get_by_record_and_model(
        db: AsyncSession, *, record_id: int, ai_model: str
    ) -> AiAnalysisResult | None:
        statement = select(AiAnalysisResult).where(
            AiAnalysisResult.record_id == record_id,
            AiAnalysisResult.ai_model == ai_model,
        )
        return await db.scalar(statement)

    @staticmethod
    async def list_by_record_id(
        db: AsyncSession, record_id: int
    ) -> list[AiAnalysisResult]:
        statement = (
            select(AiAnalysisResult)
            .where(AiAnalysisResult.record_id == record_id)
            .order_by(AiAnalysisResult.created_at.desc())
        )
        result = await db.scalars(statement)
        return list(result.all())
