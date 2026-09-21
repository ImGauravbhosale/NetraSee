from __future__ import annotations

from httpx import AsyncClient


async def register(client: AsyncClient, *, email: str, password: str = "correct-horse-battery", org_name: str = "Test Org", name: str = "Test User") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org_name, "name": name, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def csrf_headers(client: AsyncClient) -> dict:
    token = client.cookies.get("netrasee_csrf")
    return {"X-CSRF-Token": token} if token else {}
