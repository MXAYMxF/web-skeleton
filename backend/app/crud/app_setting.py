"""CRUD operations for application settings (the key/value flag store).

All database access for settings lives here; routers never query directly.
"""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.app_setting import AppSetting
from app.schemas.app_setting import AppSettingUpdate

# Sensible defaults seeded by ``ensure_defaults``. Seeding lives here (not in the
# migration) so it works identically for SQLite tests (schema via create_all) and
# real Postgres deploys (schema via Alembic).
DEFAULT_SETTINGS: Dict[str, Any] = {
    "site_name": "Web Skeleton",
    "registration_open": True,
    "maintenance_mode": False,
}


class CRUDAppSetting(CRUDBase[AppSetting, AppSettingUpdate, AppSettingUpdate]):
    """Key/value settings store with upsert + defaults seeding."""

    def get_by_key(self, db: Session, *, key: str) -> Optional[AppSetting]:
        return db.query(AppSetting).filter(AppSetting.key == key).first()

    def set(self, db: Session, *, key: str, value: Any) -> AppSetting:
        """Upsert a single setting (create if missing, otherwise update)."""
        obj = self.get_by_key(db, key=key)
        if obj is None:
            obj = AppSetting(key=key, value=value)
            db.add(obj)
        else:
            obj.value = value
            db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get_all_dict(self, db: Session) -> Dict[str, Any]:
        """Return all settings as a plain ``{key: value}`` map."""
        return {row.key: row.value for row in db.query(AppSetting).all()}

    def ensure_defaults(self, db: Session) -> Dict[str, Any]:
        """Idempotently seed any missing default settings.

        Existing values are never overwritten, so calling this repeatedly is
        safe. Returns the full current settings map.
        """
        existing = {row.key for row in db.query(AppSetting).all()}
        missing = {k: v for k, v in DEFAULT_SETTINGS.items() if k not in existing}
        if missing:
            for key, value in missing.items():
                db.add(AppSetting(key=key, value=value))
            db.commit()
        return self.get_all_dict(db)


app_setting = CRUDAppSetting(AppSetting)
