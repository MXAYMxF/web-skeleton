"""Application settings endpoints.

- ``GET  /settings`` is PUBLIC and returns only the safe ``PublicSettings`` subset
  that drives the frontend.
- ``PATCH /settings`` is superuser-only and updates one or more settings.

All DB access goes through ``crud.app_setting``.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import crud
from app.core import auth
from app.crud.app_setting import DEFAULT_SETTINGS
from app.db.session import get_db
from app.models.user import User
from app.schemas.app_setting import AppSettingUpdate, PublicSettings

router = APIRouter()

# The keys clients are allowed to read/write. They are exactly the seeded
# defaults, and all are considered safe to expose publicly.
ALLOWED_KEYS = set(DEFAULT_SETTINGS.keys())


def _public_settings(db: Session) -> PublicSettings:
    """Build the public settings view, self-seeding defaults if needed."""
    values = crud.app_setting.ensure_defaults(db)
    return PublicSettings.model_validate(values)


@router.get("", response_model=PublicSettings)
def read_public_settings(db: Session = Depends(get_db)) -> Any:
    """Public, unauthenticated read of the safe settings subset."""
    return _public_settings(db)


@router.patch("", response_model=PublicSettings)
def update_settings(
    *,
    db: Session = Depends(get_db),
    payload: Dict[str, Any],
    _current_user: User = Depends(auth.get_current_active_superuser),
) -> Any:
    """Update one or more settings (superuser only).

    Unknown keys are rejected with 400; values are type-checked against
    ``AppSettingUpdate``. Returns the updated public subset.
    """
    if not payload:
        raise HTTPException(status_code=400, detail="No settings provided")

    unknown = set(payload) - ALLOWED_KEYS
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown setting keys: {sorted(unknown)}",
        )

    # Type-check provided values (e.g. maintenance_mode must be a bool).
    try:
        validated = AppSettingUpdate.model_validate(payload).model_dump(
            exclude_unset=True
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc

    for key, value in validated.items():
        crud.app_setting.set(db, key=key, value=value)

    return _public_settings(db)
