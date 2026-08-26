"""헬스케어 테이블 생성

Revision ID: 5ed70d40e533
Revises: 
Create Date: 2026-08-26 15:35:06.699694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ed70d40e533'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "hashed_password",
            sa.String(length=255),
            nullable=False,
            comment="해시화된 비밀번호",
        ),
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column(
            "phone_number",
            sa.String(length=20),
            nullable=False,
            comment="유저 휴대폰 번호",
        ),
        sa.Column(
            "gender",
            sa.Enum("M", "F", name="gender"),
            nullable=False,
            comment="성별",
        ),
        sa.Column(
            "department",
            sa.Enum("MEDICAL", "DEV", "RESEARCH", name="department"),
            nullable=False,
            comment="소속 부서",
        ),
        sa.Column(
            "role",
            sa.Enum("PENDING", "STAFF", "ADMIN", name="role"),
            nullable=False,
            comment="부여된 역할 권한",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
            comment="계정 활성화 여부",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone_number", name="uq_users_phone_number"),
    )

    op.create_table(
        "patients",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "name", sa.String(length=30), nullable=False, comment="환자 성명"
        ),
        sa.Column(
            "age", sa.SmallInteger(), nullable=False, comment="환자 나이"
        ),
        sa.Column(
            "gender",
            sa.Enum("M", "F", name="gender"),
            nullable=True,
            comment="환자 성별",
        ),
        sa.Column(
            "phone", sa.String(length=11), nullable=False, comment="국내 전화번호"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_patients"),
    )

    op.create_table(
        "medical_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "patient_id", sa.BigInteger(), nullable=False, comment="환자 정보 ID"
        ),
        sa.Column(
            "chart_number",
            sa.String(length=50),
            nullable=False,
            comment="환자 진료 차트 번호",
        ),
        sa.Column(
            "symptoms", sa.Text(), nullable=False, comment="환자 증상 기록"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_medical_records_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_medical_records"),
        sa.UniqueConstraint(
            "chart_number", name="uq_medical_records_chart_number"
        ),
    )

    op.create_table(
        "xray_images",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "record_id", sa.BigInteger(), nullable=False, comment="진료 기록 ID"
        ),
        sa.Column(
            "uploader_id",
            sa.Integer(),
            nullable=True,
            comment="X-ray 이미지를 업로드한 유저 ID",
        ),
        sa.Column(
            "image_url", sa.String(length=2048), nullable=False, comment="이미지 URL"
        ),
        sa.Column(
            "shooting_datetime",
            sa.DateTime(),
            nullable=False,
            comment="X-ray 촬영 일시",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
            comment="X-ray 이미지 등록 일시",
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["medical_records.id"],
            name="fk_xray_images_record_id_medical_records",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploader_id"],
            ["users.id"],
            name="fk_xray_images_uploader_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_xray_images"),
    )

    op.create_table(
        "ai_analysis_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "record_id", sa.BigInteger(), nullable=False, comment="진료 기록 ID"
        ),
        sa.Column(
            "is_pneumonia", sa.Boolean(), nullable=False, comment="폐렴 진단 여부"
        ),
        sa.Column(
            "confidence",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            comment="AI 예측 신뢰도",
        ),
        sa.Column(
            "heatmap_url",
            sa.String(length=255),
            nullable=False,
            comment="병변 표시 이미지 URL",
        ),
        sa.Column(
            "ai_model",
            sa.String(length=50),
            nullable=False,
            comment="예측에 사용된 AI 모델",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["medical_records.id"],
            name="fk_ai_analysis_results_record_id_medical_records",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_analysis_results"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ai_analysis_results")
    op.drop_table("xray_images")
    op.drop_table("medical_records")
    op.drop_table("patients")
    op.drop_table("users")
