"""
Authentication endpoints with development-friendly features.
"""
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import auth
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    In development:
    - Use email: dev@example.com and password: dev for quick access
    - Or use any email with password 'dev'
    """
    # In development, allow 'dev' password for any email
    if settings.ENVIRONMENT == "development" and form_data.password == "dev":
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user:
            # Create a new user with the provided email
            user = User(
                email=form_data.username,
                hashed_password=auth.get_password_hash("dev"),
                full_name=f"Dev User ({form_data.username})",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        # Normal authentication flow
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not auth.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Update login statistics
    user.last_login = datetime.utcnow()
    user.login_count += 1
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

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
    """
    user = db.query(User).filter(User.email == user_in.email).first()
    
    if settings.ENVIRONMENT == "development":
        if user:
            # Update existing user in development
            user.full_name = user_in.full_name
            user.hashed_password = auth.get_password_hash(user_in.password)
            user.is_active = True
            db.commit()
            db.refresh(user)
        else:
            # Create new user
            user = User(
                email=user_in.email,
                hashed_password=auth.get_password_hash(user_in.password),
                full_name=user_in.full_name,
                is_active=True  # Auto-activate in development
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        # Production registration flow
        if user:
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system",
            )
        user = User(
            email=user_in.email,
            hashed_password=auth.get_password_hash(user_in.password),
            full_name=user_in.full_name,
            is_active=False  # Require activation in production
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@router.post("/test-token", response_model=UserResponse)
def test_token(current_user: User = Depends(auth.get_current_user)) -> Any:
    """
    Test access token.
    """
    return current_user
