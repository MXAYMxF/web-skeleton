"""Add user.last_failed_login for lockout window

Revision ID: 3a1b2c4d5e60
Revises: 2f3a9c4b7d10
Create Date: 2026-07-01 00:00:00.000000

Adds the nullable ``last_failed_login`` timestamp used to compute the failed
login lockout window (see ``settings.ACCOUNT_LOCKOUT_MINUTES``). Portable
``DateTime`` type so the schema matches the SQLite-portable model.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a1b2c4d5e60"
down_revision: Union[str, None] = "2f3a9c4b7d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("last_failed_login", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "last_failed_login")
