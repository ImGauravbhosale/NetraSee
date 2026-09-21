import uuid

import httpx
from httpx import AsyncClient

from tests.helpers import csrf_headers, register


def _client(app) -> AsyncClient:
    return AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_unauthenticated_request_to_protected_endpoint_is_401(client):
    resp = await client.get(f"/api/v1/orgs/{uuid.uuid4()}/controls")
    assert resp.status_code == 401


async def test_viewer_role_cannot_patch_control(app):
    async with _client(app) as owner_client:
        reg = await register(owner_client, email="owner-sec@example.com")
        org_id = reg["organization_id"]

        add_resp = await owner_client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "viewer-sec@example.com", "name": "Viewer", "role": "VIEWER", "password": "viewer-password-1"},
            headers=csrf_headers(owner_client),
        )
        assert add_resp.status_code == 201

    async with _client(app) as viewer_client:
        login_resp = await viewer_client.post(
            "/api/v1/auth/login", json={"email": "viewer-sec@example.com", "password": "viewer-password-1"}
        )
        assert login_resp.status_code == 200

        resp = await viewer_client.patch(
            f"/api/v1/orgs/{org_id}/controls/{uuid.uuid4()}",
            json={"status": "PASS"},
            headers=csrf_headers(viewer_client),
        )
        # 403 (role too low) either way — even though the control doesn't
        # exist, the role check runs first and rejects before a 404 would.
        assert resp.status_code == 403


async def test_admin_cannot_grant_owner_role(app):
    async with _client(app) as owner_client:
        reg = await register(owner_client, email="owner-priv@example.com")
        org_id = reg["organization_id"]
        await owner_client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "admin-priv@example.com", "name": "Admin", "role": "ADMIN", "password": "admin-password-1"},
            headers=csrf_headers(owner_client),
        )

    async with _client(app) as admin_client:
        await admin_client.post(
            "/api/v1/auth/login", json={"email": "admin-priv@example.com", "password": "admin-password-1"}
        )
        resp = await admin_client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "escalated@example.com", "name": "X", "role": "OWNER", "password": "some-password-12"},
            headers=csrf_headers(admin_client),
        )
        assert resp.status_code == 403


async def test_mutating_request_without_csrf_header_is_rejected(client):
    reg = await register(client, email="csrf-test@example.com")
    org_id = reg["organization_id"]

    # Intentionally omit the CSRF header despite having a valid session cookie.
    resp = await client.patch(f"/api/v1/orgs/{org_id}/controls/{uuid.uuid4()}", json={"status": "PASS"})
    assert resp.status_code == 403


async def test_malicious_string_in_status_filter_is_treated_as_data(client):
    reg = await register(client, email="sqli-test@example.com")
    org_id = reg["organization_id"]

    resp = await client.get(
        f"/api/v1/orgs/{org_id}/controls",
        params={"status_filter": "PASS'; DROP TABLE controls; --"},
    )
    # A raw SQL string simply matches nothing as an enum value — proves it
    # was never concatenated into the query. The important thing is the
    # request doesn't 500 and the table clearly still exists afterward.
    assert resp.status_code in (200, 422)

    followup = await client.get(f"/api/v1/orgs/{org_id}/controls")
    assert followup.status_code == 200


async def test_evidence_upload_rejects_disallowed_extension(client):
    reg = await register(client, email="upload-test@example.com")
    org_id = reg["organization_id"]

    resp = await client.post(
        f"/api/v1/orgs/{org_id}/evidence",
        data={"name": "malicious script", "description": "", "control_ids": "[]"},
        files={"file": ("payload.sh", b"#!/bin/sh\necho pwned", "application/x-sh")},
        headers=csrf_headers(client),
    )
    assert resp.status_code == 400
