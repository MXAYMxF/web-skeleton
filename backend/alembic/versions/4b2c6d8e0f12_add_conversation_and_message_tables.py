"""Add conversation and message tables (AI-9)

Revision ID: 4b2c6d8e0f12
Revises: 3a1b2c4d5e60
Create Date: 2026-07-02 00:00:00.000000

Creates the ``conversation`` and ``message`` tables backing AI conversation
persistence. Portable types only (``DateTime(timezone=True)``, ``String``,
``Text``, ``Integer``) so the schema matches the SQLite-portable models and the
test suite stays Postgres-free. Message rows cascade-delete with their parent
conversation (enforced in the ORM; the FK is declared here for referential
integrity on Postgres).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b2c6d8e0f12"
down_revision: Union[str, None] = "3a1b2c4d5e60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversation_id"), "conversation", ["id"], unique=False)
    op.create_index(
        op.f("ix_conversation_user_id"), "conversation", ["user_id"], unique=False
    )

    op.create_table(
        "message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_message_id"), "message", ["id"], unique=False)
    op.create_index(
        op.f("ix_message_conversation_id"), "message", ["conversation_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_message_conversation_id"), table_name="message")
    op.drop_index(op.f("ix_message_id"), table_name="message")
    op.drop_table("message")
    op.drop_index(op.f("ix_conversation_user_id"), table_name="conversation")
    op.drop_index(op.f("ix_conversation_id"), table_name="conversation")
    op.drop_table("conversation")
