"""
User-related Pydantic schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    """Shared properties."""
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    """Properties to receive via API on creation."""
    password: str

class UserUpdate(UserBase):
    """Properties to receive via API on update."""
    password: Optional[str] = None

class UserInDBBase(UserBase):
    """Properties shared by models stored in DB."""
    id: int
    is_superuser: bool = False
    
    class Config:
        from_attributes = True

class UserResponse(UserInDBBase):
    """Additional properties to return via API."""
    last_login: Optional[datetime] = None
    login_count: Optional[int] = None
