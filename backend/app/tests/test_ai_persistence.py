"""End-to-end tests for AI conversation/message persistence (AI-9).

Offline only: the provider dependency is overridden to force ``MockProvider``
(mirroring ``test_ai.py`` and how ``conftest.py`` overrides ``get_db``). Nothing
here imports an SDK or makes a network call.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud
from app.api.v1.ai import provider_dep
from app.core.ai.mock import MockProvider
from app.core.config import settings
from app.main import app
from app.schemas.user import UserCreate

AI = f"{settings.API_V1_STR}/ai"
AUTHN = f"{settings.API_V1_STR}/auth"

# The dev bearer token auto-provisions/authenticates the dev superuser.
DEV_AUTH = {"Authorization": "Bearer dev"}


@pytest.fixture(autouse=True)
def force_mock_provider():
    """Force every AI endpoint onto the deterministic MockProvider."""
    app.dependency_overrides[provider_dep] = lambda: MockProvider()
    yield
    app.dependency_overrides.pop(provider_dep, None)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post(f"{AUTHN}/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def other_token(client: TestClient, db: Session) -> str:
    """A second, distinct user (not the dev user) for ownership-isolation tests."""
    crud.user.create(
        db,
        obj_in=UserCreate(
            email="other@example.com", password="otherpass", full_name="Other"
        ),
    )
    return _login(client, "other@example.com", "otherpass")


def _chat(client: TestClient, content: str, conversation_id=None, headers=DEV_AUTH):
    body = {"messages": [{"role": "user", "content": content}]}
    if conversation_id is not None:
        body["conversation_id"] = conversation_id
    return client.post(f"{AI}/chat", headers=headers, json=body)


# --- create + persist -------------------------------------------------------


def test_chat_without_conversation_id_creates_and_persists(client):
    resp = _chat(client, "hello world")
    assert resp.status_code == 200, resp.text
    convo_id = resp.json()["conversation_id"]
    assert isinstance(convo_id, int)

    # The conversation now holds the user turn + the assistant turn.
    detail = client.get(f"{AI}/conversations/{convo_id}", headers=DEV_AUTH)
    assert detail.status_code == 200
    msgs = detail.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "hello world"
    assert "You said: hello world" in msgs[1]["content"]
    # Assistant turn records model + token accounting.
    assert msgs[1]["model"]
    assert msgs[1]["input_tokens"] is not None
    assert msgs[1]["output_tokens"] is not None


def test_followup_appends_to_same_conversation(client):
    first = _chat(client, "first message")
    convo_id = first.json()["conversation_id"]

    second = _chat(client, "second message", conversation_id=convo_id)
    assert second.status_code == 200
    assert second.json()["conversation_id"] == convo_id

    detail = client.get(f"{AI}/conversations/{convo_id}", headers=DEV_AUTH)
    roles = [m["role"] for m in detail.json()["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_chat_unknown_conversation_id_is_404(client):
    resp = _chat(client, "hi", conversation_id=999999)
    assert resp.status_code == 404


# --- listing / detail -------------------------------------------------------


def test_list_conversations_for_owner(client):
    r = _chat(client, "list me")
    convo_id = r.json()["conversation_id"]

    listing = client.get(f"{AI}/conversations", headers=DEV_AUTH)
    assert listing.status_code == 200
    items = listing.json()
    assert any(c["id"] == convo_id for c in items)
    mine = next(c for c in items if c["id"] == convo_id)
    assert mine["title"] == "list me"
    assert mine["message_count"] == 2


def test_get_conversation_returns_messages(client):
    convo_id = _chat(client, "detail me").json()["conversation_id"]
    detail = client.get(f"{AI}/conversations/{convo_id}", headers=DEV_AUTH)
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == convo_id
    assert len(body["messages"]) == 2


# --- ownership isolation ----------------------------------------------------


def test_other_user_cannot_read_or_delete(client, other_token):
    convo_id = _chat(client, "private").json()["conversation_id"]

    # Not listed for the other user.
    listing = client.get(f"{AI}/conversations", headers=_auth(other_token))
    assert listing.status_code == 200
    assert all(c["id"] != convo_id for c in listing.json())

    # 404 on read and delete for a non-owner.
    assert client.get(
        f"{AI}/conversations/{convo_id}", headers=_auth(other_token)
    ).status_code == 404
    assert client.delete(
        f"{AI}/conversations/{convo_id}", headers=_auth(other_token)
    ).status_code == 404

    # Still intact for the owner.
    assert client.get(
        f"{AI}/conversations/{convo_id}", headers=DEV_AUTH
    ).status_code == 200


def test_delete_removes_conversation(client):
    convo_id = _chat(client, "delete me").json()["conversation_id"]

    resp = client.delete(f"{AI}/conversations/{convo_id}", headers=DEV_AUTH)
    assert resp.status_code == 200
    assert resp.json()["detail"]

    # Gone afterwards.
    assert client.get(
        f"{AI}/conversations/{convo_id}", headers=DEV_AUTH
    ).status_code == 404
    assert client.delete(
        f"{AI}/conversations/{convo_id}", headers=DEV_AUTH
    ).status_code == 404


# --- streaming persistence --------------------------------------------------


def test_stream_persists_and_emits_conversation_id(client):
    resp = client.post(
        f"{AI}/chat/stream",
        headers=DEV_AUTH,
        json={"messages": [{"role": "user", "content": "stream me"}]},
    )
    assert resp.status_code == 200
    import json

    events = [
        json.loads(line[len("data: "):])
        for line in resp.text.splitlines()
        if line.startswith("data: ")
    ]
    # First event carries the conversation id; last event is the terminal done.
    assert "conversation_id" in events[0]
    convo_id = events[0]["conversation_id"]
    assert events[-1]["done"] is True

    # The assistant reply was accumulated and persisted.
    detail = client.get(f"{AI}/conversations/{convo_id}", headers=DEV_AUTH)
    msgs = detail.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert "You said: stream me" in msgs[1]["content"]
