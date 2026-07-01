"""End-to-end tests for account deactivation (self) and deletion (admin)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.schemas.user import UserCreate

AUTH = f"{settings.API_V1_STR}/auth"
USERS = f"{settings.API_V1_STR}/users"
ADMIN = f"{settings.API_V1_STR}/admin"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post(
        f"{AUTH}/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _register(client: TestClient, email: str, password: str, full_name: str = "User"):
    reg = client.post(
        f"{AUTH}/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg.status_code == 200, reg.text
    return reg.json()["access_token"]


@pytest.fixture
def superuser(db: Session):
    """Seed an active superuser."""
    user = crud.user.create(
        db,
        obj_in=UserCreate(
            email="super@example.com", password="superpass", full_name="Super"
        ),
    )
    return crud.user.update(db, db_obj=user, obj_in={"is_superuser": True})


@pytest.fixture
def normal_user(db: Session):
    """Seed an active, non-superuser user."""
    return crud.user.create(
        db,
        obj_in=UserCreate(
            email="normal@example.com", password="normalpass", full_name="Normal"
        ),
    )


@pytest.fixture
def su_token(client: TestClient, superuser) -> str:
    return _login(client, "super@example.com", "superpass")


@pytest.fixture
def normal_token(client: TestClient, normal_user) -> str:
    return _login(client, "normal@example.com", "normalpass")


# --- Self-service deactivation: DELETE /users/me -----------------------------


def test_delete_me_deactivates_account(client: TestClient, db: Session) -> None:
    token = _register(client, "bye@example.com", "secret", "Bye")

    resp = client.delete(f"{USERS}/me", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["detail"] == "Account deactivated"

    # The row is preserved but marked inactive (soft delete).
    user = crud.user.get_by_email(db, email="bye@example.com")
    assert user is not None
    assert user.is_active is False


def test_delete_me_then_authenticated_call_fails_inactive(
    client: TestClient,
) -> None:
    token = _register(client, "gone@example.com", "secret", "Gone")

    resp = client.delete(f"{USERS}/me", headers=_auth(token))
    assert resp.status_code == 200, resp.text

    # The same token now fails because the user is inactive.
    follow_up = client.get(f"{USERS}/me", headers=_auth(token))
    assert follow_up.status_code == 400, follow_up.text
    assert "Inactive" in follow_up.text


def test_delete_me_requires_auth(client: TestClient) -> None:
    resp = client.delete(f"{USERS}/me")
    assert resp.status_code == 401, resp.text


# --- Admin hard delete: DELETE /admin/users/{id} -----------------------------


def test_admin_delete_user_hard_deletes(
    client: TestClient, su_token, normal_user
) -> None:
    resp = client.delete(
        f"{ADMIN}/users/{normal_user.id}", headers=_auth(su_token)
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["detail"] == "User deleted"

    # The row is gone entirely: a follow-up GET is a 404.
    follow_up = client.get(
        f"{ADMIN}/users/{normal_user.id}", headers=_auth(su_token)
    )
    assert follow_up.status_code == 404, follow_up.text


def test_admin_delete_user_forbidden_for_non_superuser(
    client: TestClient, normal_token, superuser
) -> None:
    resp = client.delete(
        f"{ADMIN}/users/{superuser.id}", headers=_auth(normal_token)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["status_code"] == 403


def test_admin_delete_self_guard(client: TestClient, su_token, superuser) -> None:
    resp = client.delete(
        f"{ADMIN}/users/{superuser.id}", headers=_auth(su_token)
    )
    assert resp.status_code == 400, resp.text
    assert "your own account" in resp.text


def test_admin_delete_missing_user_not_found(client: TestClient, su_token) -> None:
    resp = client.delete(f"{ADMIN}/users/99999", headers=_auth(su_token))
    assert resp.status_code == 404, resp.text
