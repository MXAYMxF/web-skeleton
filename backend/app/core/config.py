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

from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, EmailStr, field_validator, model_validator

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

    # First superuser bootstrap (see app/initial_data.py). Password has no
    # default on purpose: the seed script refuses to run until it is set.
    FIRST_SUPERUSER: Optional[EmailStr] = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "app_db"
    POSTGRES_PORT: int = 5432
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
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        if isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if self.SQLALCHEMY_DATABASE_URI is None:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()
