from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base_class import Base

class User(Base):
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, index=True)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    preferences = Column(JSONB, default=dict)
    web3_address = Column(String, unique=True, index=True)
    
    # Audit fields
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
