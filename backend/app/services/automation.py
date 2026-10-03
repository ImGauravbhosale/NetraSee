"""Runs a control's bound automated check against the real connected
account and records the result the same way a human-reviewed control
would be recorded — overwritten status, a real audit event, and a real
Evidence row holding the exact API response that produced the verdict.
Nothing here is cached or simulated; every sync hits the live provider.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.models.connection import Connection
from app.models.control import Control, ControlStatus
from app.models.evidence import Evidence, EvidenceControlLink
from app.services.audit import write_audit_event
from app.services.connectors import github

# Automated evidence expires quickly on purpose: a sync from yesterday
# shouldn't silently keep passing a control forever. Re-sync is cheap, so
# the freshness bar can be tight.
_EVIDENCE_TTL = timedelta(hours=24)


async def run_control_check(
    db: AsyncSession,
    *,
    control: Control,
    connection: Connection,
    actor_user_id: uuid.UUID,
    request: Request | None = None,
) -> github.CheckResult:
    check_fn = github.CHECKS.get(control.automation_check_key or "")
    if check_fn is None:
        raise ValueError(f"Unknown automation check: {control.automation_check_key}")

    token = decrypt_secret(connection.encrypted_token)
    try:
        result = await check_fn(token, control.automation_target or "")
    except Exception as exc:  # noqa: BLE001 — network/HTTP errors must never crash a sync
        result = github.CheckResult(
            status=ControlStatus.NEEDS_REVIEW,
            summary=f"Automated check failed to run: {exc}",
            raw={"error": str(exc)},
        )

    before_state = {"status": control.status.value}
    control.status = result.status
    control.last_tested_at = datetime.now(timezone.utc)

    evidence_id = uuid.uuid4()
    raw_bytes = json.dumps(result.raw, indent=2, default=str).encode("utf-8")
    checksum = hashlib.sha256(raw_bytes).hexdigest()
    org_dir = Path(settings.evidence_storage_dir) / str(control.organization_id)
    org_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{evidence_id}.json"
    (org_dir / stored_name).write_bytes(raw_bytes)

    check_label = github.CHECK_LABELS.get(control.automation_check_key, control.automation_check_key)
    evidence = Evidence(
        id=evidence_id,
        organization_id=control.organization_id,
        name=f"{check_label} — {control.automation_target}",
        description=result.summary,
        source="github",
        collected_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + _EVIDENCE_TTL,
        owner_user_id=actor_user_id,
        checksum_sha256=checksum,
        collection_method="automated_github_api",
        file_path=str(org_dir / stored_name),
    )
    db.add(evidence)
    await db.flush()
    db.add(EvidenceControlLink(evidence_id=evidence.id, control_id=control.id))

    await write_audit_event(
        db,
        organization_id=control.organization_id,
        actor_user_id=actor_user_id,
        action="control.automated_check",
        resource_type="control",
        resource_id=str(control.id),
        before_state=before_state,
        after_state={"status": control.status.value, "summary": result.summary},
        request=request,
    )

    return result
