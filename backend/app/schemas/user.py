"""
User-related Pydantic schemas.
"""
from datetime import datetime
from typing import List, Optional
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

# --- Admin-only schemas -------------------------------------------------------
# These are deliberately separate from UserCreate/UserUpdate so that the
# self-service endpoints (e.g. PATCH /users/me) can NEVER be used to grant
# superuser status or otherwise escalate privileges. Only superuser-gated admin
# endpoints accept these.

class AdminUserCreate(UserCreate):
    """Admin create: a UserCreate that may also set the superuser flag."""
    is_superuser: bool = False

class AdminUserUpdate(BaseModel):
    """Admin update (all optional). Unlike UserUpdate, this may set is_superuser."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    preferences: Optional[dict] = None

class UserListResponse(BaseModel):
    """Paginated envelope for admin user listings."""
    items: List[UserResponse]
    total: int
    skip: int
    limit: int
