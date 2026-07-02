"""CRUD operations for AI conversations + messages (AI-9).

ALL database access for conversation/message persistence lives here — the ``ai``
router never queries the ORM directly. Every read is ownership-scoped by
``user_id`` so one user can never see or mutate another user's conversation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.conversation import Conversation, Message


class CRUDConversation(CRUDBase[Conversation, Conversation, Conversation]):
    """Conversation store with ownership-scoped reads and message appends."""

    def create_for_user(
        self, db: Session, *, user_id: int, title: Optional[str] = None
    ) -> Conversation:
        obj = Conversation(user_id=user_id, title=title)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def add_message(
        self,
        db: Session,
        *,
        conversation_id: int,
        role: str,
        content: str,
        model: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        db.add(msg)
        # Bump the parent's ``updated_at`` so most-recent-first ordering reflects
        # the latest activity, not just creation time.
        parent = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if parent is not None:
            parent.updated_at = datetime.now(timezone.utc)
            db.add(parent)
        db.commit()
        db.refresh(msg)
        return msg

    def get_for_user(
        self, db: Session, *, conversation_id: int, user_id: int
    ) -> Optional[Conversation]:
        """Return the conversation only if it exists AND is owned by ``user_id``."""
        return (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )

    def list_for_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[Conversation]:
        """Most-recently-updated conversations first."""
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_messages(self, db: Session, *, conversation_id: int) -> List[Message]:
        """All messages for a conversation, oldest first."""
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.id.asc())
            .all()
        )

    def delete_for_user(
        self, db: Session, *, conversation_id: int, user_id: int
    ) -> bool:
        """Delete a conversation (and its messages via cascade) if owned.

        Returns ``True`` if a row was deleted, ``False`` if it was missing or not
        owned by ``user_id``.
        """
        obj = self.get_for_user(db, conversation_id=conversation_id, user_id=user_id)
        if obj is None:
            return False
        db.delete(obj)
        db.commit()
        return True


conversation = CRUDConversation(Conversation)
