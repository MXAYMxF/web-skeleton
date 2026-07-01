"""Tests for the app settings store, the settings API, and the toggles."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.schemas.user import UserCreate

AUTH = f"{settings.API_V1_STR}/auth"
SETTINGS = f"{settings.API_V1_STR}/settings"
HEALTH = f"{settings.API_V1_STR}/health"
USERS = f"{settings.API_V1_STR}/users"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post(f"{AUTH}/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def superuser(db: Session):
    user = crud.user.create(
        db,
        obj_in=UserCreate(
            email="super@example.com", password="superpass", full_name="Super"
        ),
    )
    return crud.user.update(db, db_obj=user, obj_in={"is_superuser": True})


@pytest.fixture
def normal_user(db: Session):
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


# --- ensure_defaults ---------------------------------------------------------

def test_ensure_defaults_seeds_idempotently(db: Session) -> None:
    first = crud.app_setting.ensure_defaults(db)
    assert first == {
        "site_name": "Web Skeleton",
        "registration_open": True,
        "maintenance_mode": False,
    }
    # Calling again must not duplicate rows nor change values.
    second = crud.app_setting.ensure_defaults(db)
    assert second == first
    assert crud.app_setting.count(db) == 3

    # An existing value is never overwritten by a later ensure_defaults.
    crud.app_setting.set(db, key="site_name", value="Custom")
    assert crud.app_setting.ensure_defaults(db)["site_name"] == "Custom"
    assert crud.app_setting.count(db) == 3


# --- GET /settings (public) --------------------------------------------------

def test_get_public_settings_no_auth(client: TestClient) -> None:
    resp = client.get(SETTINGS)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {
        "site_name": "Web Skeleton",
        "registration_open": True,
        "maintenance_mode": False,
    }


# --- PATCH /settings (superuser only) ----------------------------------------

def test_patch_requires_superuser(client: TestClient, normal_token) -> None:
    resp = client.patch(
        SETTINGS, headers=_auth(normal_token), json={"site_name": "Nope"}
    )
    assert resp.status_code == 403, resp.text


def test_patch_requires_auth(client: TestClient) -> None:
    resp = client.patch(SETTINGS, json={"site_name": "Nope"})
    assert resp.status_code == 401, resp.text


def test_patch_updates_values(client: TestClient, su_token) -> None:
    resp = client.patch(
        SETTINGS,
        headers=_auth(su_token),
        json={"site_name": "My App", "registration_open": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["site_name"] == "My App"
    assert body["registration_open"] is False
    # Persisted: a fresh public read reflects the change.
    assert client.get(SETTINGS).json()["site_name"] == "My App"


def test_patch_unknown_key_rejected(client: TestClient, su_token) -> None:
    resp = client.patch(
        SETTINGS, headers=_auth(su_token), json={"bogus_key": True}
    )
    assert resp.status_code == 400, resp.text
    assert "Unknown setting keys" in resp.text


def test_patch_empty_body_rejected(client: TestClient, su_token) -> None:
    resp = client.patch(SETTINGS, headers=_auth(su_token), json={})
    assert resp.status_code == 400, resp.text


# --- registration_open toggle ------------------------------------------------

def test_registration_blocked_when_closed_in_production(
    client: TestClient, db: Session, monkeypatch
) -> None:
    # Non-development environment enforces the flag.
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    crud.app_setting.set(db, key="registration_open", value=False)

    resp = client.post(
        f"{AUTH}/register",
        json={"email": "new@example.com", "password": "pw", "full_name": "New"},
    )
    assert resp.status_code == 403, resp.text
    assert "closed" in resp.text


def test_registration_dev_precedence_overrides_closed(
    client: TestClient, db: Session
) -> None:
    # Default ENVIRONMENT is development: the dev convenience wins even when the
    # registration flag is closed.
    crud.app_setting.set(db, key="registration_open", value=False)
    resp = client.post(
        f"{AUTH}/register",
        json={"email": "devnew@example.com", "password": "pw", "full_name": "Dev"},
    )
    assert resp.status_code == 200, resp.text


# --- maintenance_mode toggle -------------------------------------------------

def test_maintenance_mode_blocks_non_superuser(
    client: TestClient, db: Session, su_token, normal_token
) -> None:
    # Turn maintenance on (tokens were already minted while it was off).
    crud.app_setting.set(db, key="maintenance_mode", value=True)

    # Health stays reachable (it is defined outside the guarded api_router).
    assert client.get(HEALTH).status_code == 200

    # Public settings read stays reachable (allow-listed).
    assert client.get(SETTINGS).status_code == 200

    # Login stays reachable so a superuser can sign in to turn it off.
    assert (
        client.post(
            f"{AUTH}/login",
            data={"username": "normal@example.com", "password": "normalpass"},
        ).status_code
        == 200
    )

    # A normal user hitting a protected route gets 503.
    resp = client.get(f"{USERS}/me", headers=_auth(normal_token))
    assert resp.status_code == 503, resp.text
    assert "maintenance" in resp.text

    # A superuser still gets through (and can turn maintenance off).
    assert client.get(f"{USERS}/me", headers=_auth(su_token)).status_code == 200
    off = client.patch(
        SETTINGS, headers=_auth(su_token), json={"maintenance_mode": False}
    )
    assert off.status_code == 200, off.text
    assert off.json()["maintenance_mode"] is False

    # Maintenance lifted: the normal user is served again.
    assert client.get(f"{USERS}/me", headers=_auth(normal_token)).status_code == 200
