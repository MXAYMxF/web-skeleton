"""
Admin user-management endpoints (superuser only).

Every endpoint is gated by ``auth.get_current_active_superuser``; non-superusers
receive 403. These endpoints use the dedicated ``Admin*`` schemas, which (unlike
the self-service ``UserUpdate``) may set ``is_superuser``.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.core import auth
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    AdminUserCreate,
    AdminUserUpdate,
    UserListResponse,
    UserResponse,
)

router = APIRouter()


@router.get("/users", response_model=UserListResponse)
def list_users(
    *,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    q: Optional[str] = None,
    _current_user: User = Depends(auth.get_current_active_superuser),
) -> Any:
    """List users with pagination and an optional case-insensitive search.

    ``q`` matches against email OR full_name. ``total`` is the count for the
    (filtered) query, not just the returned page.
    """
    items = crud.user.search(db, q=q, skip=skip, limit=limit)
    total = crud.user.count_search(db, q=q)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    _current_user: User = Depends(auth.get_current_active_superuser),
) -> Any:
    """Fetch a single user by id."""
    user = crud.user.get(db, id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post(
    "/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: AdminUserCreate,
    _current_user: User = Depends(auth.get_current_active_superuser),
) -> Any:
    """Create a user (optionally a superuser)."""
    existing = crud.user.get_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    return crud.user.create_admin(db, obj_in=user_in)


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    user_in: AdminUserUpdate,
    current_user: User = Depends(auth.get_current_active_superuser),
) -> Any:
    """Update a user.

    Guards against an acting superuser locking themselves out: they may not
    remove their own superuser status nor deactivate themselves.
    """
    user = crud.user.get(db, id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Self-protection guards.
    if user_id == current_user.id:
        if user_in.is_superuser is False:
            raise HTTPException(
                status_code=400,
                detail="You cannot remove your own superuser status",
            )
        if user_in.is_active is False:
            raise HTTPException(
                status_code=400,
                detail="You cannot deactivate your own account",
            )

    # Email uniqueness guard (only if it actually changes).
    if user_in.email and user_in.email != user.email:
        existing = crud.user.get_by_email(db, email=user_in.email)
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system",
            )

    return crud.user.update(db, db_obj=user, obj_in=user_in)
