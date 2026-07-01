"""SQLAlchemy model for application-wide settings.

A tiny key/value store for runtime-tunable flags (e.g. ``registration_open``,
``maintenance_mode``, ``site_name``). Values are stored as portable ``JSON`` so a
single column can hold booleans, strings or numbers and the model stays
SQLite-portable (no Postgres-only ``JSONB``), which keeps the test suite
Postgres-free.

``created_at`` / ``updated_at`` (timezone-aware) are inherited from ``Base``.
"""
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class AppSetting(Base):
    # ``Base`` would derive the table name as ``appsetting``; pin the conventional
    # snake_case name explicitly so migrations and queries are unambiguous.
    __tablename__ = "app_setting"

    # The setting name is the primary key (one row per setting, inherently unique).
    key: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # The value, stored as a JSON scalar (true / "Web Skeleton" / 42, ...).
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
