from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, require_org_role
from app.core.db import get_db
from app.models.audit_event import AuditEvent
from app.models.membership import Role
from app.schemas.audit import AuditEventOut

router = APIRouter(prefix="/api/v1/orgs/{org_id}/audit-log", tags=["audit-log"])


@router.get("", response_model=list[AuditEventOut])
async def list_audit_log(
    org_id: uuid.UUID,
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.organization_id == org_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(500)
    )
    return [AuditEventOut.model_validate(e) for e in result.scalars().all()]
