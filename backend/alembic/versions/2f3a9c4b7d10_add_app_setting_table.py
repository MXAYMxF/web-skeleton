"""Add app_setting table

Revision ID: 2f3a9c4b7d10
Revises: 1c51dd39c7b4
Create Date: 2026-07-01 00:00:00.000000

Creates the key/value ``app_setting`` table. Portable types only (``JSON``, not
``JSONB``) so the schema matches the SQLite-portable model. Default rows are NOT
seeded here; ``crud.app_setting.ensure_defaults`` does that at runtime so seeding
works identically for SQLite tests and Postgres deploys.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f3a9c4b7d10"
down_revision: Union[str, None] = "1c51dd39c7b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_setting",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(op.f("ix_app_setting_key"), "app_setting", ["key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_app_setting_key"), table_name="app_setting")
    op.drop_table("app_setting")
