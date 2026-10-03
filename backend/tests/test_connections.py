"""Integration tests for connections + control automation. The GitHub
HTTP calls themselves are already covered against realistic responses in
test_connectors_github.py — here we monkeypatch at the connector-function
boundary to test NetraSee's own API behavior: encryption at rest, audit
trail, tenant isolation, and the PATCH-is-blocked-once-automated rule.
"""
import uuid

import pytest

from app.models.control import ControlStatus
from app.services.connectors import github
from tests.helpers import csrf_headers, register


async def _create_control(client, org_id, **overrides):
    payload = {
        "control_key": "CTRL-AUTO-1",
        "name": "Automated control",
        "description": "desc",
        "objective": "objective",
        "category": "Access Control",
    }
    payload.update(overrides)
    resp = await client.post(f"/api/v1/orgs/{org_id}/controls", json=payload, headers=csrf_headers(client))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_connection(client, org_id, monkeypatch, login="octocat"):
    async def fake_validate_token(token: str) -> str:
        return login

    monkeypatch.setattr(github, "validate_token", fake_validate_token)
    resp = await client.post(
        f"/api/v1/orgs/{org_id}/connections",
        json={"provider": "GITHUB", "token": "ghp_faketoken"},
        headers=csrf_headers(client),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_connection_never_returns_raw_token(client, monkeypatch):
    reg = await register(client, email="conn1@example.com")
    org_id = reg["organization_id"]

    connection = await _create_connection(client, org_id, monkeypatch)
    assert connection["account_login"] == "octocat"
    assert "token" not in connection
    assert "encrypted_token" not in connection


async def test_create_connection_rejects_invalid_token(client, monkeypatch):
    reg = await register(client, email="conn2@example.com")
    org_id = reg["organization_id"]

    async def fake_validate_token(token: str) -> str:
        raise github.GithubAuthError("GitHub rejected this token")

    monkeypatch.setattr(github, "validate_token", fake_validate_token)
    resp = await client.post(
        f"/api/v1/orgs/{org_id}/connections",
        json={"provider": "GITHUB", "token": "bad"},
        headers=csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_bind_automation_and_sync_updates_control_status(client, monkeypatch):
    reg = await register(client, email="conn3@example.com")
    org_id = reg["organization_id"]
    control = await _create_control(client, org_id)
    connection = await _create_connection(client, org_id, monkeypatch)

    bind_resp = await client.post(
        f"/api/v1/orgs/{org_id}/controls/{control['id']}/automation",
        json={"connection_id": connection["id"], "check_key": "github.branch_protection", "target": "acme/widgets"},
        headers=csrf_headers(client),
    )
    assert bind_resp.status_code == 200, bind_resp.text
    assert bind_resp.json()["automation_status"] == "AUTOMATED"

    async def fake_check(token: str, target: str) -> github.CheckResult:
        return github.CheckResult(ControlStatus.PASS, f"{target} looks good", {"ok": True})

    monkeypatch.setitem(github.CHECKS, "github.branch_protection", fake_check)

    sync_resp = await client.post(
        f"/api/v1/orgs/{org_id}/connections/{connection['id']}/sync", headers=csrf_headers(client)
    )
    assert sync_resp.status_code == 200, sync_resp.text
    results = sync_resp.json()["results"]
    assert len(results) == 1
    assert results[0]["status"] == "PASS"

    control_resp = await client.get(f"/api/v1/orgs/{org_id}/controls/{control['id']}")
    body = control_resp.json()
    assert body["status"] == "PASS"
    assert len(body["evidence"]) == 1  # sync creates a real Evidence row citing the raw API response

    audit_resp = await client.get(f"/api/v1/orgs/{org_id}/audit-log")
    actions = [e["action"] for e in audit_resp.json()]
    assert "control.automated_check" in actions
    assert "control.automation_bound" in actions


async def test_automated_control_rejects_manual_status_patch(client, monkeypatch):
    reg = await register(client, email="conn4@example.com")
    org_id = reg["organization_id"]
    control = await _create_control(client, org_id)
    connection = await _create_connection(client, org_id, monkeypatch)

    await client.post(
        f"/api/v1/orgs/{org_id}/controls/{control['id']}/automation",
        json={"connection_id": connection["id"], "check_key": "github.org_2fa_enforced", "target": "acme"},
        headers=csrf_headers(client),
    )

    patch_resp = await client.patch(
        f"/api/v1/orgs/{org_id}/controls/{control['id']}",
        json={"status": "PASS"},
        headers=csrf_headers(client),
    )
    assert patch_resp.status_code == 409


async def test_unbind_automation_allows_manual_patch_again(client, monkeypatch):
    reg = await register(client, email="conn5@example.com")
    org_id = reg["organization_id"]
    control = await _create_control(client, org_id)
    connection = await _create_connection(client, org_id, monkeypatch)

    await client.post(
        f"/api/v1/orgs/{org_id}/controls/{control['id']}/automation",
        json={"connection_id": connection["id"], "check_key": "github.org_2fa_enforced", "target": "acme"},
        headers=csrf_headers(client),
    )
    unbind_resp = await client.delete(
        f"/api/v1/orgs/{org_id}/controls/{control['id']}/automation", headers=csrf_headers(client)
    )
    assert unbind_resp.status_code == 200
    assert unbind_resp.json()["automation_status"] == "MANUAL"

    patch_resp = await client.patch(
        f"/api/v1/orgs/{org_id}/controls/{control['id']}",
        json={"status": "PASS"},
        headers=csrf_headers(client),
    )
    assert patch_resp.status_code == 200


async def test_org_b_cannot_sync_org_a_connection(client, monkeypatch):
    reg_a = await register(client, email="conn6a@example.com")
    org_a = reg_a["organization_id"]
    connection = await _create_connection(client, org_a, monkeypatch)

    await client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    reg_b = await register(client, email="conn6b@example.com")
    org_b = reg_b["organization_id"]

    # Deliberately using org_b in the path with org_a's connection id —
    # must 404, not leak that the connection exists under a different org.
    resp = await client.post(
        f"/api/v1/orgs/{org_b}/connections/{connection['id']}/sync", headers=csrf_headers(client)
    )
    assert resp.status_code == 404


async def test_delete_connection_unbinds_dependent_controls(client, monkeypatch):
    reg = await register(client, email="conn7@example.com")
    org_id = reg["organization_id"]
    control = await _create_control(client, org_id)
    connection = await _create_connection(client, org_id, monkeypatch)

    await client.post(
        f"/api/v1/orgs/{org_id}/controls/{control['id']}/automation",
        json={"connection_id": connection["id"], "check_key": "github.org_2fa_enforced", "target": "acme"},
        headers=csrf_headers(client),
    )

    delete_resp = await client.delete(
        f"/api/v1/orgs/{org_id}/connections/{connection['id']}", headers=csrf_headers(client)
    )
    assert delete_resp.status_code == 204

    control_resp = await client.get(f"/api/v1/orgs/{org_id}/controls/{control['id']}")
    body = control_resp.json()
    assert body["automation_status"] == "MANUAL"
    assert body["automation_connection_id"] is None
