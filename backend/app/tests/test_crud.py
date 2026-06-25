from sqlalchemy.orm import Session

from app import crud
from app.schemas.user import UserCreate

def test_create_user(db: Session) -> None:
    email = "test@example.com"
    password = "test_password"
    user_in = UserCreate(email=email, password=password)
    user = crud.user.create(db, obj_in=user_in)
    assert user.email == email
    assert hasattr(user, "hashed_password")

def test_authenticate_user(db: Session) -> None:
    email = "test@example.com"
    password = "test_password"
    user_in = UserCreate(email=email, password=password)
    user = crud.user.create(db, obj_in=user_in)
    authenticated_user = crud.user.authenticate(
        db, email=email, password=password
    )
    assert authenticated_user
    assert user.email == authenticated_user.email

def test_not_authenticate_user(db: Session) -> None:
    email = "test@example.com"
    password = "test_password"
    user = crud.user.authenticate(db, email=email, password=password)
    assert user is None
