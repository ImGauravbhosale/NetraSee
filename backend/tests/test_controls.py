from tests.helpers import csrf_headers, register


async def _create_control(client, org_id, **overrides):
    payload = {
        "control_key": "CTRL-TEST-1",
        "name": "Test control",
        "description": "desc",
        "objective": "objective",
        "category": "Access Control",
    }
    payload.update(overrides)
    resp = await client.post(f"/api/v1/orgs/{org_id}/controls", json=payload, headers=csrf_headers(client))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_and_list_control(client):
    reg = await register(client, email="controls@example.com")
    org_id = reg["organization_id"]

    created = await _create_control(client, org_id)
    assert created["status"] == "NOT_TESTED"

    listed = await client.get(f"/api/v1/orgs/{org_id}/controls")
    assert listed.status_code == 200
    assert any(c["id"] == created["id"] for c in listed.json())


async def test_patch_control_status_creates_audit_event(client):
    reg = await register(client, email="controls2@example.com")
    org_id = reg["organization_id"]
    control = await _create_control(client, org_id)

    patch_resp = await client.patch(
        f"/api/v1/orgs/{org_id}/controls/{control['id']}",
        json={"status": "PASS"},
        headers=csrf_headers(client),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "PASS"

    audit_resp = await client.get(f"/api/v1/orgs/{org_id}/audit-log")
    assert audit_resp.status_code == 200
    actions = [e["action"] for e in audit_resp.json()]
    assert "control.updated" in actions
    assert "control.created" in actions


async def test_get_nonexistent_control_is_404(client):
    reg = await register(client, email="controls3@example.com")
    org_id = reg["organization_id"]
    import uuid

    resp = await client.get(f"/api/v1/orgs/{org_id}/controls/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_dashboard_reflects_real_control_counts(client):
    reg = await register(client, email="controls4@example.com")
    org_id = reg["organization_id"]

    c1 = await _create_control(client, org_id, control_key="CTRL-A")
    await client.patch(f"/api/v1/orgs/{org_id}/controls/{c1['id']}", json={"status": "PASS"}, headers=csrf_headers(client))
    c2 = await _create_control(client, org_id, control_key="CTRL-B")
    await client.patch(f"/api/v1/orgs/{org_id}/controls/{c2['id']}", json={"status": "FAIL"}, headers=csrf_headers(client))

    dash = await client.get(f"/api/v1/orgs/{org_id}/dashboard")
    assert dash.status_code == 200
    body = dash.json()
    assert body["controls"]["passing"] == 1
    assert body["controls"]["failing"] == 1
