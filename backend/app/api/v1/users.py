"""
User self-management endpoints.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.core import auth
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(auth.get_current_active_user),
) -> Any:
    """Return the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_current_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(auth.get_current_active_user),
) -> Any:
    """
    Update the currently authenticated user (full_name, email, password,
    preferences).

    Note: the JWT subject is the email, so changing the email invalidates the
    current access token. Clients must re-authenticate after an email change.
    """
    if user_in.email and user_in.email != current_user.email:
        existing = crud.user.get_by_email(db, email=user_in.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system",
            )

    user = crud.user.update(db, db_obj=current_user, obj_in=user_in)
    return user


@router.delete("/me")
def deactivate_current_user(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_active_user),
) -> Any:
    """Deactivate (soft-delete) the currently authenticated user.

    Sets ``is_active = False``; the row is preserved. The caller's access token
    keeps its signature but subsequent authenticated requests will fail with a
    400 (inactive user), so clients should clear their session afterwards.
    """
    crud.user.deactivate(db, user=current_user)
    return {"detail": "Account deactivated"}
