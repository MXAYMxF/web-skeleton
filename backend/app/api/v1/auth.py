"""
Authentication endpoints with development-friendly features.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud
from app.core import auth
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


def _token_response(user: User) -> dict:
    """Build a Token payload (access token + user) for a given user."""
    access_token = auth.create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }


@router.post("/login", response_model=Token)
async def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.

    In development:
    - Use email: dev@example.com and password: dev for quick access
    - Or use any email with password 'dev' (auto-provisions the account)
    """
    user = crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if user is None:
        # In development, the 'dev' master password auto-provisions the account.
        if settings.ENVIRONMENT == "development" and form_data.password == "dev":
            user = crud.user.get_by_email(db, email=form_data.username) or crud.user.create(
                db,
                obj_in=UserCreate(
                    email=form_data.username,
                    password="dev",
                    full_name=f"Dev User ({form_data.username})",
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Update login statistics
    user.last_login = datetime.now(timezone.utc)
    user.login_count += 1
    db.commit()
    db.refresh(user)

    return _token_response(user)


@router.post("/register", response_model=Token)
async def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Register a new user.

    In development:
    - Automatically activates users
    - Allows registration even if email exists (updates the user instead)

    Honors the ``registration_open`` setting. Precedence: the development
    convenience wins, so the skeleton stays easy to use locally; in
    staging/production a closed registration returns 403.
    """
    if settings.ENVIRONMENT != "development":
        flags = crud.app_setting.get_all_dict(db)
        if not flags.get("registration_open", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is currently closed",
            )

    existing = crud.user.get_by_email(db, email=user_in.email)

    if existing and settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )

    if existing:
        # Development convenience: update the existing account in place.
        user = crud.user.update(
            db,
            db_obj=existing,
            obj_in={
                "full_name": user_in.full_name,
                "hashed_password": auth.get_password_hash(user_in.password),
                "is_active": True,
            },
        )
    else:
        user = crud.user.create(db, obj_in=user_in)
        if settings.ENVIRONMENT != "development":
            # Production: require activation before the account is usable.
            user = crud.user.update(db, db_obj=user, obj_in={"is_active": False})

    return _token_response(user)


@router.post("/test-token", response_model=UserResponse)
def test_token(current_user: User = Depends(auth.get_current_user)) -> Any:
    """
    Test access token.
    """
    return current_user
