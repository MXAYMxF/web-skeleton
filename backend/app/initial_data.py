"""Idempotent seed script: ensure the first superuser exists.

Run after migrations::

    alembic upgrade head
    python -m app.initial_data

Requires ``FIRST_SUPERUSER`` and ``FIRST_SUPERUSER_PASSWORD`` (env or .env).
Safe to run repeatedly.
"""
import logging

from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db(db: Session) -> None:
    """Ensure the configured first superuser exists. Idempotent."""
    if not settings.FIRST_SUPERUSER_PASSWORD:
        raise RuntimeError(
            "FIRST_SUPERUSER_PASSWORD is not set. Set it (env var or .env) "
            "before seeding the first superuser."
        )

    user = crud.user.get_or_create_superuser(
        db,
        email=settings.FIRST_SUPERUSER,
        password=settings.FIRST_SUPERUSER_PASSWORD,
    )
    logger.info("Superuser ready: %s", user.email)


def main() -> None:
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
