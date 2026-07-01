"""
API router configuration.

A router-wide ``maintenance_mode`` guard is attached here. Because the health
check (defined directly on the app in ``main.py``) is NOT part of this router, it
stays reachable during maintenance automatically.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import crud
from app.core import auth
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

# Paths that remain reachable while maintenance_mode is on, so a superuser can log
# in and turn it off and the frontend can still read the (public) settings.
_MAINTENANCE_ALLOWLIST = {
    f"{settings.API_V1_STR}/auth/login",  # superusers (and anyone) can authenticate
    f"{settings.API_V1_STR}/settings",    # public read of the safe settings subset
}


def maintenance_guard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(auth.get_optional_current_user),
) -> None:
    """Block non-superuser API traffic when ``maintenance_mode`` is on.

    Returns 503 for everyone except superusers (who must still be able to manage
    the system) and the small allow-list above. CORS preflight (``OPTIONS``) is
    always let through. Reads the flag via ``crud.app_setting`` (one cheap query).
    """
    if request.method == "OPTIONS":
        return

    flags = crud.app_setting.get_all_dict(db)
    if not flags.get("maintenance_mode", False):
        return  # Not in maintenance: nothing to do.

    if request.url.path in _MAINTENANCE_ALLOWLIST:
        return

    if current_user is not None and current_user.is_superuser:
        return

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The service is temporarily down for maintenance",
    )


# All v1 routes are subject to the maintenance guard.
api_router = APIRouter(dependencies=[Depends(maintenance_guard)])

# Imported after api_router so module import order stays clean.
from app.api.v1 import admin, auth as auth_routes, settings as settings_routes, users  # noqa: E402

api_router.include_router(auth_routes.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(settings_routes.router, prefix="/settings", tags=["settings"])
