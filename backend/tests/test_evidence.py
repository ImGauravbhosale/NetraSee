from tests.helpers import csrf_headers, register


async def test_upload_and_list_evidence(client):
    reg = await register(client, email="evidence1@example.com")
    org_id = reg["organization_id"]

    resp = await client.post(
        f"/api/v1/orgs/{org_id}/evidence",
        data={"name": "MFA screenshot", "description": "proof", "control_ids": "[]"},
        files={"file": ("proof.png", b"\x89PNG fake bytes", "image/png")},
        headers=csrf_headers(client),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "VALID"
    assert len(body["checksum_sha256"]) == 64

    listed = await client.get(f"/api/v1/orgs/{org_id}/evidence")
    assert listed.status_code == 200
    assert any(e["id"] == body["id"] for e in listed.json())


async def test_upload_rejects_oversized_file(client):
    reg = await register(client, email="evidence2@example.com")
    org_id = reg["organization_id"]

    huge = b"x" * (26 * 1024 * 1024)  # over the 25MB limit
    resp = await client.post(
        f"/api/v1/orgs/{org_id}/evidence",
        data={"name": "huge file", "description": "", "control_ids": "[]"},
        files={"file": ("big.pdf", huge, "application/pdf")},
        headers=csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_delete_evidence_creates_audit_event_and_removes_file(client):
    reg = await register(client, email="evidence3@example.com")
    org_id = reg["organization_id"]

    upload = await client.post(
        f"/api/v1/orgs/{org_id}/evidence",
        data={"name": "temp evidence", "description": "", "control_ids": "[]"},
        files={"file": ("temp.txt", b"hello", "text/plain")},
        headers=csrf_headers(client),
    )
    evidence_id = upload.json()["id"]

    delete_resp = await client.delete(f"/api/v1/orgs/{org_id}/evidence/{evidence_id}", headers=csrf_headers(client))
    assert delete_resp.status_code == 204

    listed = await client.get(f"/api/v1/orgs/{org_id}/evidence")
    assert all(e["id"] != evidence_id for e in listed.json())

    audit_resp = await client.get(f"/api/v1/orgs/{org_id}/audit-log")
    actions = [e["action"] for e in audit_resp.json()]
    assert "evidence.deleted" in actions
