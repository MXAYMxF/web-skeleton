"""
Main FastAPI application module for Web-Skeleton Project.
"""
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.session import get_db

app = FastAPI(
    title="Web-Skeleton API",
    description="A modular web application skeleton with FastAPI backend",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Set up CORS middleware. Driven by settings; falls back to the dev frontend.
cors_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS] or [
    "http://localhost:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint for health check and API identification."""
    return {
        "app_name": "Web-Skeleton",
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs",
        "openapi_url": f"{settings.API_V1_STR}/openapi.json"
    }

@app.get(f"{settings.API_V1_STR}/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with database connection test."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "app": "Web-Skeleton API",
        "status": "healthy",
        "version": settings.VERSION,
        "database": db_status,
        "environment": settings.ENVIRONMENT
    }

@app.get(f"{settings.API_V1_STR}/config")
async def get_config():
    """Get application configuration (safe values only)."""
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "api_v1_str": settings.API_V1_STR
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"status_code": exc.status_code, "detail": exc.detail}},
        headers=getattr(exc, "headers", None),
    )
