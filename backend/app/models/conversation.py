"""SQLAlchemy models for AI conversation/message persistence (AI-9).

A ``Conversation`` groups an ordered list of ``Message`` rows for a single user.
Both are deliberately SQLite-portable — only portable column types (``String``,
``Text``, ``Integer``, ``DateTime``) so the test suite runs on SQLite without
Postgres. ``created_at`` / ``updated_at`` (timezone-aware) are inherited from
``Base``; ``Conversation.updated_at`` bumps on every write, which is what the
"most-recent first" listing orders by.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"), index=True, nullable=False
    )
    # Nullable — derived (truncated) from the first user message, or left null.
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # ``created_at`` / ``updated_at`` (timezone-aware) come from ``Base``.

    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )

    @property
    def message_count(self) -> int:
        """Number of messages, for the summary schema. Lazy-loads the relationship
        (fine at skeleton scale); the detail schema already needs the full list."""
        return len(self.messages)


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversation.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # user|assistant|system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Provider/usage metadata — only meaningful for assistant turns; nullable so a
    # user/system turn can omit them.
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ``created_at`` / ``updated_at`` (timezone-aware) come from ``Base``; messages
    # are immutable so only ``created_at`` is meaningful (used for ordering).

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
