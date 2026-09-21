import pytest

from tests.helpers import csrf_headers, register


async def test_register_creates_org_and_logs_in(client):
    data = await register(client, email="owner@example.com")
    assert "organization_id" in data
    assert client.cookies.get("netrasee_session") is not None


async def test_register_duplicate_email_rejected(client):
    await register(client, email="dup@example.com")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": "Other", "name": "X", "email": "dup@example.com", "password": "another-password-1"},
    )
    assert resp.status_code == 409


async def test_login_with_correct_password(client):
    await register(client, email="login@example.com", password="correct-horse-battery")
    resp = await client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "correct-horse-battery"})
    assert resp.status_code == 200


async def test_login_with_wrong_password_rejected(client):
    await register(client, email="wrongpw@example.com", password="correct-horse-battery")
    resp = await client.post("/api/v1/auth/login", json={"email": "wrongpw@example.com", "password": "nope-wrong"})
    assert resp.status_code == 401


async def test_login_nonexistent_user_rejected(client):
    resp = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever12345"})
    assert resp.status_code == 401


async def test_me_requires_authentication(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_returns_membership_after_register(client):
    await register(client, email="me@example.com", org_name="Me Corp")
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "me@example.com"
    assert len(body["memberships"]) == 1
    assert body["memberships"][0]["organization_name"] == "Me Corp"
    assert body["memberships"][0]["role"] == "OWNER"


async def test_logout_invalidates_session(client):
    await register(client, email="logout@example.com")
    resp = await client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert resp.status_code == 200

    resp2 = await client.get("/api/v1/auth/me")
    assert resp2.status_code == 401


async def test_login_rate_limiting_kicks_in_after_repeated_failures(client):
    await register(client, email="ratelimited@example.com", password="correct-horse-battery")
    responses = []
    for _ in range(12):
        resp = await client.post(
            "/api/v1/auth/login", json={"email": "ratelimited@example.com", "password": "wrong-password"}
        )
        responses.append(resp.status_code)
    assert 429 in responses
