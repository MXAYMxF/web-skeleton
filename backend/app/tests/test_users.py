"""End-to-end tests for the users self-management endpoints."""
from fastapi.testclient import TestClient

from app.core.config import settings

AUTH = f"{settings.API_V1_STR}/auth"
USERS = f"{settings.API_V1_STR}/users"


def _register(client: TestClient, email: str, password: str, full_name: str = "User"):
    reg = client.post(
        f"{AUTH}/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg.status_code == 200, reg.text
    return reg.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_get_me_returns_current_user(client: TestClient) -> None:
    token = _register(client, "me@example.com", "secret", "Me")
    resp = client.get(f"{USERS}/me", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "me@example.com"
    assert body["full_name"] == "Me"


def test_patch_me_updates_full_name_and_preferences(client: TestClient) -> None:
    token = _register(client, "edit@example.com", "secret")
    resp = client.patch(
        f"{USERS}/me",
        headers=_auth(token),
        json={"full_name": "Edited Name", "preferences": {"theme": "dark"}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["full_name"] == "Edited Name"
    assert body["preferences"] == {"theme": "dark"}


def test_patch_me_change_password_allows_new_login(client: TestClient) -> None:
    token = _register(client, "pw@example.com", "oldpass")
    resp = client.patch(
        f"{USERS}/me",
        headers=_auth(token),
        json={"password": "newpass"},
    )
    assert resp.status_code == 200, resp.text

    # New password works.
    login = client.post(
        f"{AUTH}/login",
        data={"username": "pw@example.com", "password": "newpass"},
    )
    assert login.status_code == 200, login.text


def test_patch_me_duplicate_email_rejected(client: TestClient) -> None:
    _register(client, "taken@example.com", "secret")
    token = _register(client, "mover@example.com", "secret")
    resp = client.patch(
        f"{USERS}/me",
        headers=_auth(token),
        json={"email": "taken@example.com"},
    )
    assert resp.status_code == 400, resp.text
    assert "already exists" in resp.text
