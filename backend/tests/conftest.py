"""Tests run against a real Postgres database (NETRASEE_TEST_DATABASE_URL,
defaulting to a `netrasee_test` database on the same local Postgres) —
deliberately not SQLite, since the schema uses JSONB and native UUID
types whose behavior SQLite can't faithfully stand in for.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db import get_db
from app.models import Base

TEST_DATABASE_URL = os.environ.get(
    "NETRASEE_TEST_DATABASE_URL",
    "postgresql+asyncpg://netrasee:netrasee@localhost:5432/netrasee_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def _create_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def _truncate_between_tests(_create_schema):
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def db_session():
    async with TestSessionFactory() as session:
        yield session


@pytest.fixture
def app():
    from app.main import app as fastapi_app

    async def _override_get_db():
        async with TestSessionFactory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
