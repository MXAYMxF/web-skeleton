"""
User-related Pydantic schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr

class UserBase(BaseModel):
    """Shared properties."""
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    """Properties to receive via API on creation."""
    password: str

class UserUpdate(BaseModel):
    """Properties to receive via API on update (all optional for partial edits)."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    preferences: Optional[dict] = None

class UserInDBBase(UserBase):
    """Properties shared by models stored in DB."""
    id: int
    is_superuser: bool = False

    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserInDBBase):
    """Additional properties to return via API."""
    last_login: Optional[datetime] = None
    login_count: Optional[int] = None
    preferences: Optional[dict] = None
