import json
from fastapi.testclient import TestClient
import pytest
from cryptography.fernet import Fernet
from cli_anything.amazon_ads_ops_workbench.control_plane.app import create_app
from cli_anything.amazon_ads_ops_workbench.control_plane.settings import Settings
from cli_anything.amazon_ads_ops_workbench.control_plane.security import Actor, Problem


class FakeService:
    def __init__(self, settings):
        self.settings = settings

    def authenticate_session(self, raw):
        if raw != "test-session":
            raise Problem(401, "not signed in")
        return Actor("user", "session"), "admin"

    def authenticate_token(self, raw):
        if raw != "amcp_test":
            raise Problem(401, "bad token")
        return Actor("user", "token", frozenset({"ads:read"}), ("account",), "token-id")

    def accounts(self, actor):
        assert actor.user_id == "user"
        return [{"id": "account", "label": "fixture"}]

    def approve(self, *args):
        raise AssertionError("Unauthenticated approval reached service")

    def setup_state(self):
        return {"needs_setup": True, "token_required": False, "available": True}

    def reset_password(self, username, password, setup_token, ip):
        assert (username, password, setup_token) == ("owner", "long-password-1", "")
        return {"reset": True}

    def change_password(self, actor, raw_session, password):
        assert (actor.kind, raw_session, password) == (
            "session",
            "test-session",
            "long-password-2",
        )
        return {"changed": True}

    def setup_admin(self, username, password, setup_token):
        assert (username, password, setup_token) == ("owner", "long-password-1", "")
        return "setup-session"


@pytest.fixture
def client():
    settings = Settings(
        "postgresql+psycopg://unused", Fernet.generate_key().decode(), "x" * 40
    )
    with TestClient(
        create_app(settings, FakeService(settings)), base_url="http://127.0.0.1:16666"
    ) as client:
        yield client


def test_bearer_cannot_approve_web_plan(client):
    result = client.post(
        "/api/tasks/x/approve",
        headers={
            "Origin": "http://127.0.0.1:16666",
            "Authorization": "Bearer amcp_test",
        },
        json={"confirm_text": "确认", "payload_hash": "a" * 64},
    )
    assert result.status_code == 401


def test_cross_origin_write_denied(client):
    result = client.post("/api/logout", headers={"Origin": "https://evil.example"})
    assert result.status_code == 403


def test_session_requires_csrf(client):
    client.cookies.set("ads_session", "test-session")
    result = client.post(
        "/api/tasks/x/approve",
        headers={"Origin": "http://127.0.0.1:16666"},
        json={"confirm_text": "确认", "payload_hash": "a" * 64},
    )
    assert result.status_code == 403


def test_invalid_inputs_do_not_echo_credentials(client):
    result = client.post(
        "/api/login",
        headers={"Origin": "http://127.0.0.1:16666"},
        json={"username": "x", "password": "", "extra": "never-echo-secret"},
    )
    assert result.status_code == 422 and "never-echo-secret" not in result.text


def test_mcp_initialize_list_call_and_authentication(client):
    headers = {
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer amcp_test",
    }
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    assert client.post("/mcp/", json=body).status_code == 401
    response = client.post("/mcp/", headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["result"]["serverInfo"]["name"] == "Amazon Ads Control Plane"
    listed = client.post(
        "/mcp/",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ).json()
    names = [t["name"] for t in listed["result"]["tools"]]
    # Confirmation is a separate, scope-gated tool; there is no direct execute.
    assert {"ads_plan_change", "ads_confirm_change"} <= set(names)
    assert not any("execute" in name for name in names)
    result = client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "ads_accounts", "arguments": {}},
        },
    ).json()
    assert not result["result"].get("isError"), result
    assert "fixture" in json.dumps(result)

def test_capability_catalog_http_and_mcp_serialization(client):
    client.cookies.set('ads_session','test-session')
    response=client.get('/api/capabilities')
    assert response.status_code==200
    assert len(response.json())>=120
    result=client.post('/mcp/',headers={'Accept':'application/json, text/event-stream','Authorization':'Bearer amcp_test'},json={'jsonrpc':'2.0','id':10,'method':'tools/call','params':{'name':'ads_capabilities','arguments':{}}})
    assert result.status_code==200 and not result.json()['result'].get('isError'),result.text


def test_setup_state_is_public(client):
    result = client.get("/api/setup")
    assert result.status_code == 200 and result.json()["needs_setup"] is True


def test_setup_signs_in_and_rejects_cross_origin(client):
    body = {"username": "owner", "password": "long-password-1"}
    denied = client.post(
        "/api/setup", headers={"Origin": "https://evil.example"}, json=body
    )
    assert denied.status_code == 403
    result = client.post(
        "/api/setup", headers={"Origin": "http://127.0.0.1:16666"}, json=body
    )
    assert result.status_code == 200, result.text
    assert result.json()["username"] == "owner" and result.json()["csrf_token"]
    assert result.cookies.get("ads_session") == "setup-session"


def test_reset_password_is_public_but_same_origin(client):
    body = {"username": "owner", "password": "long-password-1"}
    denied = client.post(
        "/api/password/reset", headers={"Origin": "https://evil.example"}, json=body
    )
    assert denied.status_code == 403
    result = client.post(
        "/api/password/reset", headers={"Origin": "http://127.0.0.1:16666"}, json=body
    )
    assert result.status_code == 200 and result.json() == {"reset": True}
    assert "ads_session" not in result.cookies


def test_change_password_requires_session_and_csrf(client):
    origin = {"Origin": "http://127.0.0.1:16666"}
    body = {"password": "long-password-2"}
    assert client.post("/api/password", headers=origin, json=body).status_code == 401
    client.cookies.set("ads_session", "test-session")
    assert client.post("/api/password", headers=origin, json=body).status_code == 403
    session = client.get("/api/session").json()
    result = client.post(
        "/api/password",
        headers={**origin, "X-CSRF-Token": session["csrf_token"]},
        json=body,
    )
    assert result.status_code == 200 and result.json() == {"changed": True}
