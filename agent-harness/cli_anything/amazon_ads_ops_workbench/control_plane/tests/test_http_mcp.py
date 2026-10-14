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
    assert "ads_plan_change" in names and not any(
        "approve" in name or "execute" in name for name in names
    )
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
