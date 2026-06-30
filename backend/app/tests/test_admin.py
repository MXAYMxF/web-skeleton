"""End-to-end tests for the superuser-only admin user-management endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.schemas.user import UserCreate

AUTH = f"{settings.API_V1_STR}/auth"
ADMIN = f"{settings.API_V1_STR}/admin"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post(
        f"{AUTH}/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


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


def test_non_superuser_forbidden(client, normal_token) -> None:
    resp = client.get(f"{ADMIN}/users", headers=_auth(normal_token))
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["status_code"] == 403


def test_list_users_envelope(client, su_token, normal_user) -> None:
    resp = client.get(f"{ADMIN}/users", headers=_auth(su_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # superuser + normal_user seeded.
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["skip"] == 0
    assert body["limit"] == 100
    emails = {u["email"] for u in body["items"]}
    assert emails == {"super@example.com", "normal@example.com"}


def test_list_users_search_filters(client, su_token, normal_user) -> None:
    resp = client.get(f"{ADMIN}/users", headers=_auth(su_token), params={"q": "normal"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["email"] == "normal@example.com"

    # Case-insensitive match on full_name too.
    resp = client.get(f"{ADMIN}/users", headers=_auth(su_token), params={"q": "SUPER"})
    assert resp.json()["total"] == 1


def test_get_user_by_id(client, su_token, normal_user) -> None:
    resp = client.get(f"{ADMIN}/users/{normal_user.id}", headers=_auth(su_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "normal@example.com"


def test_get_user_not_found(client, su_token) -> None:
    resp = client.get(f"{ADMIN}/users/99999", headers=_auth(su_token))
    assert resp.status_code == 404, resp.text


def test_create_user_including_superuser(client, su_token) -> None:
    resp = client.post(
        f"{ADMIN}/users",
        headers=_auth(su_token),
        json={
            "email": "made@example.com",
            "password": "pw",
            "full_name": "Made",
            "is_superuser": True,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "made@example.com"
    assert body["is_superuser"] is True


def test_create_user_duplicate_email(client, su_token, normal_user) -> None:
    resp = client.post(
        f"{ADMIN}/users",
        headers=_auth(su_token),
        json={"email": "normal@example.com", "password": "pw"},
    )
    assert resp.status_code == 400, resp.text
    assert "already exists" in resp.text


def test_patch_other_user_toggles_flags(client, su_token, normal_user) -> None:
    resp = client.patch(
        f"{ADMIN}/users/{normal_user.id}",
        headers=_auth(su_token),
        json={"is_active": False, "is_superuser": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_active"] is False
    assert body["is_superuser"] is True


def test_patch_other_user_not_found(client, su_token) -> None:
    resp = client.patch(
        f"{ADMIN}/users/99999", headers=_auth(su_token), json={"is_active": False}
    )
    assert resp.status_code == 404, resp.text


def test_self_demotion_guard(client, su_token, superuser) -> None:
    resp = client.patch(
        f"{ADMIN}/users/{superuser.id}",
        headers=_auth(su_token),
        json={"is_superuser": False},
    )
    assert resp.status_code == 400, resp.text
    assert "superuser status" in resp.text


def test_self_deactivation_guard(client, su_token, superuser) -> None:
    resp = client.patch(
        f"{ADMIN}/users/{superuser.id}",
        headers=_auth(su_token),
        json={"is_active": False},
    )
    assert resp.status_code == 400, resp.text
    assert "deactivate" in resp.text
