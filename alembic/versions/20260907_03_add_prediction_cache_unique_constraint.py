"""add prediction cache unique constraint

Revision ID: 20260907_03
Revises: 20260827_02
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260907_03"
down_revision: str | None = "20260827_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_ai_analysis_results_record_model"


def upgrade() -> None:
    # 이미 중복된 행이 있는 개발 DB에서도 migration이 적용되도록 가장
    # 먼저 생성된 결과만 남긴 뒤 DB 레벨 유일 제약을 추가한다.
    op.execute(
        """
        DELETE duplicate_result
        FROM ai_analysis_results AS duplicate_result
        INNER JOIN ai_analysis_results AS original_result
          ON duplicate_result.record_id = original_result.record_id
         AND duplicate_result.ai_model = original_result.ai_model
         AND duplicate_result.id > original_result.id
        """
    )
    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "ai_analysis_results",
        ["record_id", "ai_model"],
    )


def downgrade() -> None:
    op.drop_constraint(
        CONSTRAINT_NAME,
        "ai_analysis_results",
        type_="unique",
    )
