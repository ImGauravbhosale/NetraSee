"""Seeds the global framework/requirement catalog only — no demo org, no
demo user, no fake controls or evidence. Safe to run against a real
deployment: Framework and Requirement are a shared catalog, not org data,
and this is idempotent (re-running adds nothing new once seeded).

Usage: uv run python scripts/seed_frameworks.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import async_session_factory
from app.services.framework_catalog import CATALOG, ensure_catalog_seeded


async def seed() -> None:
    async with async_session_factory() as db:
        frameworks = await ensure_catalog_seeded(db)
        await db.commit()
        for key, name, _, requirements in CATALOG:
            print(f"  {name} ({key}) — {len(requirements)} requirements")
        print(f"Seeded {len(frameworks)} frameworks into the global catalog.")


if __name__ == "__main__":
    asyncio.run(seed())
