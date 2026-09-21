"""The single most important test file in this project. Every one of
these must fail closed (403/404) — a User B session must never be able to
read or write anything belonging to Organization A, by any endpoint.

Each test uses two separate AsyncClient instances (separate cookie jars)
against the same app, so client_a's session cookie never leaks into
client_b's requests.
"""
import uuid

import httpx
from httpx import AsyncClient

from tests.helpers import csrf_headers, register


def _client(app) -> AsyncClient:
    return AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_user_b_cannot_list_user_a_controls(app):
    async with _client(app) as client_a:
        org_a = (await register(client_a, email="a-owner@example.com"))["organization_id"]

    async with _client(app) as client_b:
        await register(client_b, email="b-owner@example.com")
        resp = await client_b.get(f"/api/v1/orgs/{org_a}/controls")
        assert resp.status_code == 404


async def test_user_b_cannot_read_user_a_dashboard(app):
    async with _client(app) as client_a:
        org_a = (await register(client_a, email="a2-owner@example.com"))["organization_id"]

    async with _client(app) as client_b:
        await register(client_b, email="b2-owner@example.com")
        resp = await client_b.get(f"/api/v1/orgs/{org_a}/dashboard")
        assert resp.status_code == 404


async def test_user_b_cannot_patch_user_a_control(app):
    async with _client(app) as client_a:
        org_a = (await register(client_a, email="a3-owner@example.com"))["organization_id"]

    # A made-up-but-valid-shaped UUID — proves the org-membership check
    # runs before any control lookup would even matter.
    fake_control_id = str(uuid.uuid4())

    async with _client(app) as client_b:
        await register(client_b, email="b3-owner@example.com")
        resp = await client_b.patch(
            f"/api/v1/orgs/{org_a}/controls/{fake_control_id}",
            json={"status": "PASS"},
            headers=csrf_headers(client_b),
        )
        assert resp.status_code == 404


async def test_user_b_cannot_delete_user_a_evidence(app):
    async with _client(app) as client_a:
        org_a = (await register(client_a, email="a4-owner@example.com"))["organization_id"]

    fake_evidence_id = str(uuid.uuid4())

    async with _client(app) as client_b:
        await register(client_b, email="b4-owner@example.com")
        resp = await client_b.delete(
            f"/api/v1/orgs/{org_a}/evidence/{fake_evidence_id}", headers=csrf_headers(client_b)
        )
        assert resp.status_code == 404


async def test_user_b_cannot_view_user_a_audit_log(app):
    async with _client(app) as client_a:
        org_a = (await register(client_a, email="a5-owner@example.com"))["organization_id"]

    async with _client(app) as client_b:
        await register(client_b, email="b5-owner@example.com")
        resp = await client_b.get(f"/api/v1/orgs/{org_a}/audit-log")
        assert resp.status_code == 404


async def test_user_b_cannot_add_themselves_as_member_of_org_a(app):
    async with _client(app) as client_a:
        org_a = (await register(client_a, email="a6-owner@example.com"))["organization_id"]

    async with _client(app) as client_b:
        await register(client_b, email="b6-owner@example.com")
        resp = await client_b.post(
            f"/api/v1/orgs/{org_a}/members",
            json={"email": "intruder@example.com", "name": "Intruder", "role": "ADMIN", "password": "whatever123456"},
            headers=csrf_headers(client_b),
        )
        assert resp.status_code == 404
