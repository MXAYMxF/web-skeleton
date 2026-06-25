"""End-to-end auth endpoint tests (development environment)."""
from fastapi.testclient import TestClient

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
