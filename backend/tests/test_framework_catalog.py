from sqlalchemy import func, select

from app.models.framework import Framework, Requirement
from app.services.framework_catalog import CATALOG, ensure_catalog_seeded


async def test_ensure_catalog_seeded_creates_every_framework(db_session):
    await ensure_catalog_seeded(db_session)
    await db_session.commit()

    result = await db_session.execute(select(func.count(Framework.id)))
    assert result.scalar_one() == len(CATALOG)

    for key, _, _, requirements in CATALOG:
        fw = (await db_session.execute(select(Framework).where(Framework.key == key))).scalar_one()
        count = (
            await db_session.execute(select(func.count(Requirement.id)).where(Requirement.framework_id == fw.id))
        ).scalar_one()
        assert count == len(requirements), f"{key} expected {len(requirements)} requirements, got {count}"


async def test_ensure_catalog_seeded_is_idempotent(db_session):
    await ensure_catalog_seeded(db_session)
    await db_session.commit()
    await ensure_catalog_seeded(db_session)
    await db_session.commit()

    result = await db_session.execute(select(func.count(Framework.id)))
    assert result.scalar_one() == len(CATALOG)  # re-running adds nothing new


async def test_global_frameworks_endpoint_lists_full_catalog(client, db_session):
    await ensure_catalog_seeded(db_session)
    await db_session.commit()

    resp = await client.get("/api/v1/frameworks")
    assert resp.status_code == 200
    keys = {f["key"] for f in resp.json()}
    assert keys == {key for key, _, _, _ in CATALOG}
