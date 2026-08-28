"""enforce required user fields

Revision ID: 20260827_02
Revises: 20260826_01
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_02"
down_revision: str | None = "20260826_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "users",
        "name",
        existing_type=sa.String(length=20),
        nullable=False,
    )
    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.String(length=20),
        nullable=False,
    )
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("PENDING", "STAFF", "ADMIN", name="role"),
        existing_nullable=False,
        server_default="PENDING",
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("PENDING", "STAFF", "ADMIN", name="role"),
        existing_nullable=False,
        server_default=None,
    )
    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.String(length=20),
        nullable=True,
    )
    op.alter_column(
        "users",
        "name",
        existing_type=sa.String(length=20),
        nullable=True,
    )
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=True,
    )
