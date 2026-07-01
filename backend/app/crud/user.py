"""CRUD operations for the User model."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import get_password_hash, verify_password
from app.core.config import settings
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import AdminUserCreate, UserCreate, UserUpdate


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

    def deactivate(self, db: Session, *, user: User) -> User:
        """Soft-delete a user by clearing ``is_active``.

        The row is preserved (unlike ``remove``); the user simply can no longer
        authenticate, since ``get_current_active_user`` rejects inactive users.
        """
        return self.update(db, db_obj=user, obj_in={"is_active": False})

    def create_admin(self, db: Session, *, obj_in: AdminUserCreate) -> User:
        """Create a user from admin input, honoring the ``is_superuser`` flag.

        Reuses ``create`` (password hashing lives there) then promotes if
        requested, so hashing logic is never duplicated.
        """
        user = self.create(
            db,
            obj_in=UserCreate(
                email=obj_in.email,
                password=obj_in.password,
                full_name=obj_in.full_name,
                is_active=obj_in.is_active,
            ),
        )
        if obj_in.is_superuser:
            user = self.update(db, db_obj=user, obj_in={"is_superuser": True})
        return user

    def _search_query(self, db: Session, *, q: Optional[str]):
        """Build a (case-insensitive) filtered query over email/full_name."""
        query = db.query(User)
        if q:
            pattern = f"%{q}%"
            query = query.filter(
                or_(User.email.ilike(pattern), User.full_name.ilike(pattern))
            )
        return query

    def search(
        self, db: Session, *, q: Optional[str], skip: int = 0, limit: int = 100
    ) -> List[User]:
        return (
            self._search_query(db, q=q)
            .order_by(User.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_search(self, db: Session, *, q: Optional[str]) -> int:
        return self._search_query(db, q=q).count()

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

    def get_or_create_dev_user(
        self, db: Session, *, email: str, superuser: bool = False
    ) -> User:
        """Idempotently get-or-create the development auto-provisioned user.

        Single home for the dev "backdoor" account creation (used by both the
        dev bearer-token path in ``core.auth.get_current_user`` and the dev
        master-password path in ``/auth/login``). Callers are responsible for
        gating this to ``settings.ENVIRONMENT == "development"``.

        Creates an ACTIVE user with a hashed ``"dev"`` password. Pass
        ``superuser=True`` for the dev-token superuser (``dev@example.com``);
        the default is an ordinary user, matching the login auto-provision.
        """
        user = self.get_by_email(db, email=email)
        if user is None:
            user = self.create(
                db,
                obj_in=UserCreate(
                    email=email,
                    password="dev",
                    full_name=f"Dev User ({email})",
                    is_active=True,
                ),
            )
        if superuser and not user.is_superuser:
            user = self.update(db, db_obj=user, obj_in={"is_superuser": True})
        return user

    def is_locked(self, user: User) -> bool:
        """Whether ``user`` is currently within the failed-login lockout window.

        Locked when failed attempts have reached the threshold AND the last
        failure is still inside the ``ACCOUNT_LOCKOUT_MINUTES`` window. Once the
        window elapses the account is usable again (the counter is cleared on
        the next successful login).
        """
        if user.failed_login_attempts < settings.MAX_FAILED_LOGIN_ATTEMPTS:
            return False
        last = user.last_failed_login
        if last is None:
            return False
        # SQLite returns naive datetimes; treat stored values as UTC.
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        window = timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
        return datetime.now(timezone.utc) < last + window

    def register_failed_login(self, db: Session, *, user: User) -> User:
        """Record a failed password attempt (increment counter + timestamp)."""
        return self.update(
            db,
            db_obj=user,
            obj_in={
                "failed_login_attempts": user.failed_login_attempts + 1,
                "last_failed_login": datetime.now(timezone.utc),
            },
        )

    def record_successful_login(self, db: Session, *, user: User) -> User:
        """Clear failed-login state and stamp login statistics on success."""
        return self.update(
            db,
            db_obj=user,
            obj_in={
                "failed_login_attempts": 0,
                "last_failed_login": None,
                "last_login": datetime.now(timezone.utc),
                "login_count": user.login_count + 1,
            },
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
