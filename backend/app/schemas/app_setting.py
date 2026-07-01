"""Pydantic v2 schemas for application settings."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AppSettingRead(BaseModel):
    """A single setting row as returned from the DB."""

    key: str
    value: Any
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AppSettingUpdate(BaseModel):
    """Typed body for ``PATCH /settings``.

    Every field is optional so callers may update one or many settings at once
    (partial update). ``extra="forbid"`` rejects unknown keys at validation time;
    the endpoint additionally surfaces a friendly 400 for unknown keys.
    """

    site_name: Optional[str] = None
    registration_open: Optional[bool] = None
    maintenance_mode: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class PublicSettings(BaseModel):
    """The safe, public subset of settings exposed to unauthenticated clients.

    Every field here is intentionally non-sensitive and drives the frontend.
    """

    site_name: str
    registration_open: bool
    maintenance_mode: bool
