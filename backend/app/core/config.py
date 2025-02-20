"""Configuration Management Module
-----------------------------

This module handles all configuration settings for the application using Pydantic's BaseSettings.
It loads configuration from environment variables and provides type checking and validation.

Key Features:
    - Environment variable loading with validation
    - Secure password and key handling
    - Database connection management
    - Email configuration
    - Web3 integration settings
    - Caching configuration
    - API rate limiting settings

Usage:
    from app.core.config import settings
    
    # Access settings
    database_url = settings.SQLALCHEMY_DATABASE_URI
    jwt_secret = settings.SECRET_KEY

Environment Variables:
    All settings can be overridden using environment variables.
    See .env.example for all available options.
"""

import secrets
from typing import Any, Dict, List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, EmailStr, validator, SecretStr

class Settings(BaseSettings):
    """Application settings class that handles all configuration.
    
    Attributes:
        PROJECT_NAME (str): Name of the project
        VERSION (str): Current version of the application
        API_V1_STR (str): API version prefix
        ENVIRONMENT (str): Current environment (development, staging, production)
        DEBUG (bool): Debug mode flag
    """
    PROJECT_NAME: str = "Web Skeleton"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "app_db"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # Web3
    WEB3_PROVIDER_URI: str = "http://localhost:8545"
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}/{values.get('POSTGRES_DB')}"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
