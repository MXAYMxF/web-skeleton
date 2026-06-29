"""CRUD operations for the User model."""
from typing import Any, Dict, Optional, Union

from sqlalchemy.orm import Session

from app.core.auth import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """User CRUD with password hashing and authentication."""

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            is_active=obj_in.is_active if obj_in.is_active is not None else True,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: User,
        obj_in: Union[UserUpdate, Dict[str, Any]],
    ) -> User:
        # Normalize to a plain dict of fields the caller actually set.
        if isinstance(obj_in, dict):
            update_data = dict(obj_in)
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # Convert a provided password into the stored hashed_password.
        password = update_data.pop("password", None)
        if password:
            update_data["hashed_password"] = get_password_hash(password)

        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def get_or_create_superuser(
        self, db: Session, *, email: str, password: str
    ) -> User:
        """Idempotently ensure an active superuser with ``email`` exists.

        If the user already exists, promote it to an active superuser without
        touching its password. Otherwise create it, then promote. Calling this
        twice yields the same single user.
        """
        user = self.get_by_email(db, email=email)
        if user is None:
            user = self.create(
                db,
                obj_in=UserCreate(
                    email=email,
                    password=password,
                    full_name="Initial Superuser",
                    is_active=True,
                ),
            )
        return self.update(
            db, db_obj=user, obj_in={"is_superuser": True, "is_active": True}
        )

    def authenticate(
        self, db: Session, *, email: str, password: str
    ) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


user = CRUDUser(User)
