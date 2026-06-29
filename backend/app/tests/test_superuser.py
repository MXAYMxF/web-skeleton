"""Tests for superuser gating, the get_or_create helper, and the seed script."""
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.core.auth import get_current_active_superuser
from app.core.config import settings
from app.initial_data import init_db
from app.models.user import User


def test_get_current_active_superuser_allows_superuser(db: Session) -> None:
    user = User(
        email="boss@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert get_current_active_superuser(current_user=user) is user


def test_get_current_active_superuser_rejects_non_superuser(db: Session) -> None:
    user = User(
        email="plain@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    with pytest.raises(HTTPException) as exc_info:
        get_current_active_superuser(current_user=user)
    assert exc_info.value.status_code == 403


def test_get_or_create_superuser_is_idempotent(db: Session) -> None:
    first = crud.user.get_or_create_superuser(
        db, email="seed@example.com", password="secret"
    )
    assert first.is_superuser is True
    assert first.is_active is True

    second = crud.user.get_or_create_superuser(
        db, email="seed@example.com", password="ignored"
    )
    assert second.id == first.id
    assert second.is_superuser is True


def test_init_db_creates_superuser(db: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "FIRST_SUPERUSER", "first@example.com")
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_PASSWORD", "topsecret")

    init_db(db)

    user = crud.user.get_by_email(db, email="first@example.com")
    assert user is not None
    assert user.is_superuser is True
    assert user.is_active is True


def test_init_db_requires_password(db: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "FIRST_SUPERUSER", "first@example.com")
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_PASSWORD", None)

    with pytest.raises(RuntimeError):
        init_db(db)
