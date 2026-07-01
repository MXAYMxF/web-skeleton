"""End-to-end auth endpoint tests (development environment)."""
from fastapi.testclient import TestClient

from app import crud
from app.core.config import settings

PREFIX = "/api/v1/auth"


def test_register_then_login_and_test_token(client: TestClient) -> None:
    reg = client.post(
        f"{PREFIX}/register",
        json={"email": "a@b.com", "password": "secret", "full_name": "A"},
    )
    assert reg.status_code == 200, reg.text
    body = reg.json()
    assert body["access_token"]
    assert body["user"]["email"] == "a@b.com"

    login = client.post(
        f"{PREFIX}/login",
        data={"username": "a@b.com", "password": "secret"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    me = client.post(
        f"{PREFIX}/test-token",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "a@b.com"


def test_dev_password_autoprovisions_user(client: TestClient) -> None:
    login = client.post(
        f"{PREFIX}/login",
        data={"username": "new@dev.com", "password": "dev"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["email"] == "new@dev.com"


def test_wrong_password_rejected(client: TestClient) -> None:
    client.post(
        f"{PREFIX}/register",
        json={"email": "c@d.com", "password": "right"},
    )
    login = client.post(
        f"{PREFIX}/login",
        data={"username": "c@d.com", "password": "wrong"},
    )
    assert login.status_code == 401


def test_dev_token_yields_superuser(client: TestClient) -> None:
    """The dev bearer token resolves to a working superuser (T23 preserved)."""
    me = client.post(
        f"{PREFIX}/test-token",
        headers={"Authorization": "Bearer dev"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "dev@example.com"
    assert me.json()["is_superuser"] is True


def test_failed_attempts_increment_then_lockout(
    client: TestClient, db, monkeypatch
) -> None:
    """After MAX failed attempts the account is 403-locked, even if the
    password later becomes correct. Force non-dev so 'dev' isn't a master pw."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "MAX_FAILED_LOGIN_ATTEMPTS", 3)

    client.post(f"{PREFIX}/register", json={"email": "lock@d.com", "password": "right"})

    for i in range(1, settings.MAX_FAILED_LOGIN_ATTEMPTS + 1):
        r = client.post(
            f"{PREFIX}/login",
            data={"username": "lock@d.com", "password": "wrong"},
        )
        assert r.status_code == 401, r.text
        user = crud.user.get_by_email(db, email="lock@d.com")
        assert user.failed_login_attempts == i

    # Now locked: even the correct password is rejected with 403.
    r = client.post(
        f"{PREFIX}/login",
        data={"username": "lock@d.com", "password": "right"},
    )
    assert r.status_code == 403, r.text
    assert "locked" in r.json()["error"]["detail"].lower()


def test_success_before_cap_resets_counter(
    client: TestClient, db, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "MAX_FAILED_LOGIN_ATTEMPTS", 5)

    client.post(f"{PREFIX}/register", json={"email": "reset@d.com", "password": "right"})

    for _ in range(3):
        client.post(
            f"{PREFIX}/login",
            data={"username": "reset@d.com", "password": "wrong"},
        )
    assert crud.user.get_by_email(db, email="reset@d.com").failed_login_attempts == 3

    ok = client.post(
        f"{PREFIX}/login",
        data={"username": "reset@d.com", "password": "right"},
    )
    assert ok.status_code == 200, ok.text
    assert crud.user.get_by_email(db, email="reset@d.com").failed_login_attempts == 0


def test_dev_master_password_bypasses_lockout(
    client: TestClient, db, monkeypatch
) -> None:
    """The dev master password must never be locked out and resets the counter."""
    monkeypatch.setattr(settings, "MAX_FAILED_LOGIN_ATTEMPTS", 3)

    client.post(f"{PREFIX}/register", json={"email": "devlock@d.com", "password": "right"})
    # Drive the account into a locked state directly.
    user = crud.user.get_by_email(db, email="devlock@d.com")
    for _ in range(3):
        crud.user.register_failed_login(db, user=user)
    assert crud.user.is_locked(user) is True

    # In development, the 'dev' master password still logs in and resets state.
    ok = client.post(
        f"{PREFIX}/login",
        data={"username": "devlock@d.com", "password": "dev"},
    )
    assert ok.status_code == 200, ok.text
    assert crud.user.get_by_email(db, email="devlock@d.com").failed_login_attempts == 0
