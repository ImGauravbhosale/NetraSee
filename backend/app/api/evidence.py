from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, require_org_role
from app.core.config import settings
from app.core.db import get_db
from app.models.control import Control
from app.models.evidence import Evidence, EvidenceControlLink
from app.models.membership import Role
from app.schemas.evidence import EvidenceControlRef, EvidenceOut
from app.services.audit import write_audit_event
from app.services.evidence_status import effective_status

router = APIRouter(prefix="/api/v1/orgs/{org_id}/evidence", tags=["evidence"])

_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".json", ".csv", ".zip"}
_MAX_UPLOAD_BYTES = settings.max_evidence_upload_mb * 1024 * 1024


async def _serialize(evidence: Evidence, db: AsyncSession) -> EvidenceOut:
    link_result = await db.execute(
        select(Control)
        .join(EvidenceControlLink, EvidenceControlLink.control_id == Control.id)
        .where(EvidenceControlLink.evidence_id == evidence.id)
    )
    controls = [
        EvidenceControlRef(control_id=c.id, control_key=c.control_key, control_name=c.name)
        for c in link_result.scalars().all()
    ]
    return EvidenceOut(
        id=evidence.id,
        name=evidence.name,
        description=evidence.description,
        source=evidence.source,
        collected_at=evidence.collected_at,
        expires_at=evidence.expires_at,
        status=effective_status(evidence.status, evidence.expires_at),
        checksum_sha256=evidence.checksum_sha256,
        collection_method=evidence.collection_method,
        owner_user_id=evidence.owner_user_id,
        controls=controls,
    )


@router.get("", response_model=list[EvidenceOut])
async def list_evidence(
    org_id: uuid.UUID, ctx: OrgContext = Depends(require_org_role(Role.VIEWER)), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Evidence).where(Evidence.organization_id == org_id).order_by(Evidence.name))
    return [await _serialize(e, db) for e in result.scalars().all()]


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    org_id: uuid.UUID,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    expires_at: datetime | None = Form(None),
    control_ids: str = Form("[]"),  # JSON array of UUID strings — form-data can't carry a real list cleanly
    file: UploadFile = File(...),
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"File type {suffix or '(none)'} is not allowed")

    contents = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"File exceeds {settings.max_evidence_upload_mb}MB limit")

    try:
        control_id_list = [uuid.UUID(x) for x in json.loads(control_ids)]
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "control_ids must be a JSON array of UUIDs")

    checksum = hashlib.sha256(contents).hexdigest()
    evidence_id = uuid.uuid4()
    # Generated filename, never the client-supplied one — avoids path
    # traversal / overwrite tricks via a crafted original filename.
    stored_name = f"{evidence_id}{suffix}"
    org_dir = Path(settings.evidence_storage_dir) / str(org_id)
    org_dir.mkdir(parents=True, exist_ok=True)
    (org_dir / stored_name).write_bytes(contents)

    evidence = Evidence(
        id=evidence_id,
        organization_id=org_id,
        name=name,
        description=description,
        source="manual",
        collected_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        owner_user_id=ctx.user.id,
        checksum_sha256=checksum,
        collection_method="manual_upload",
        file_path=str(org_dir / stored_name),
    )
    db.add(evidence)

    if control_id_list:
        result = await db.execute(
            select(Control).where(Control.id.in_(control_id_list), Control.organization_id == org_id)
        )
        valid_controls = result.scalars().all()
        for control in valid_controls:
            db.add(EvidenceControlLink(evidence_id=evidence.id, control_id=control.id))

    await write_audit_event(
        db,
        organization_id=org_id,
        actor_user_id=ctx.user.id,
        action="evidence.uploaded",
        resource_type="evidence",
        resource_id=str(evidence.id),
        after_state={"name": name, "checksum_sha256": checksum},
        request=request,
    )

    await db.commit()
    await db.refresh(evidence)
    return await _serialize(evidence, db)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    org_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request: Request,
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    evidence = await db.get(Evidence, evidence_id)
    if evidence is None or evidence.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")

    before_state = {"name": evidence.name, "checksum_sha256": evidence.checksum_sha256}
    await write_audit_event(
        db,
        organization_id=org_id,
        actor_user_id=ctx.user.id,
        action="evidence.deleted",
        resource_type="evidence",
        resource_id=str(evidence.id),
        before_state=before_state,
        request=request,
    )

    file_path = Path(evidence.file_path)
    await db.delete(evidence)
    await db.commit()

    if file_path.exists():
        file_path.unlink()
