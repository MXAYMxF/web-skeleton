"""
Token-related Pydantic schemas.
"""
from typing import Optional
from pydantic import BaseModel
from app.schemas.user import UserResponse

class Token(BaseModel):
    """Token schema with user information."""
    access_token: str
    token_type: str
    user: Optional[UserResponse] = None
