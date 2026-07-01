"""
Authentication utilities with development-friendly options.
"""
from datetime import datetime, timedelta
from typing import Optional, Union

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
# A non-erroring variant: yields ``None`` instead of raising when no bearer token
# is present. Used by the maintenance-mode guard, which must treat anonymous
# requests as "not a superuser" rather than reject them outright.
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False
)

# bcrypt only considers the first 72 bytes of a password.
_BCRYPT_MAX_BYTES = 72


def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against a provided password."""
    # In development, allow 'dev' as a master password
    if settings.ENVIRONMENT == "development" and plain_password == "dev":
        return True
    pw = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(pw, hashed_password.encode("utf-8"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get the current user from the token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # In development, allow a special dev token that maps to a superuser dev
    # account. Creation lives in one place (crud.user.get_or_create_dev_user).
    if settings.ENVIRONMENT == "development" and token == "dev":
        from app import crud  # local import avoids a crud <-> core.auth cycle

        return crud.user.get_or_create_dev_user(
            db, email="dev@example.com", superuser=True
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    from app import crud  # local import avoids a crud <-> core.auth cycle

    user = crud.user.get_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

async def get_optional_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(optional_oauth2_scheme),
) -> Optional[User]:
    """Resolve the current user if a (valid) token is present, else ``None``.

    Never raises on missing/invalid credentials — it simply returns ``None`` so
    callers can make their own decision (e.g. the maintenance guard).
    """
    if not token:
        return None
    try:
        return await get_current_user(db=db, token=token)
    except HTTPException:
        return None


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require an active superuser. Single source of truth for admin gating."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
