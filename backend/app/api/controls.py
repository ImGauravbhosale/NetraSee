from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, require_org_role
from app.core.db import get_db
from app.models.control import Control, ControlRequirementLink, ControlStatus
from app.models.evidence import Evidence, EvidenceControlLink
from app.models.framework import Framework, Requirement
from app.models.membership import Role
from app.models.framework import Requirement
from app.schemas.control import (
    ControlCreateRequest,
    ControlDetailOut,
    ControlEvidenceOut,
    ControlListItemOut,
    ControlUpdateRequest,
    RequirementMappingOut,
)
from app.services.audit import write_audit_event
from app.services.evidence_status import effective_status

router = APIRouter(prefix="/api/v1/orgs/{org_id}/controls", tags=["controls"])


@router.get("", response_model=list[ControlListItemOut])
async def list_controls(
    org_id: uuid.UUID,
    status_filter: ControlStatus | None = None,
    ctx: OrgContext = Depends(require_org_role(Role.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    query = select(Control).where(Control.organization_id == org_id)
    if status_filter:
        query = query.where(Control.status == status_filter)
    result = await db.execute(query.order_by(Control.control_key))
    return [ControlListItemOut.model_validate(c) for c in result.scalars().all()]


@router.post("", response_model=ControlDetailOut, status_code=status.HTTP_201_CREATED)
async def create_control(
    org_id: uuid.UUID,
    payload: ControlCreateRequest,
    request: Request,
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    control = Control(
        organization_id=org_id,
        control_key=payload.control_key,
        name=payload.name,
        description=payload.description,
        objective=payload.objective,
        category=payload.category,
        automation_status=payload.automation_status,
        testing_frequency=payload.testing_frequency,
    )
    db.add(control)
    await db.flush()

    if payload.requirement_ids:
        result = await db.execute(select(Requirement).where(Requirement.id.in_(payload.requirement_ids)))
        for requirement in result.scalars().all():
            db.add(ControlRequirementLink(control_id=control.id, requirement_id=requirement.id))

    await write_audit_event(
        db,
        organization_id=org_id,
        actor_user_id=ctx.user.id,
        action="control.created",
        resource_type="control",
        resource_id=str(control.id),
        after_state={"control_key": control.control_key, "name": control.name},
        request=request,
    )

    await db.commit()
    await db.refresh(control)
    return await _load_detail(control, db)


async def _load_detail(control: Control, db: AsyncSession) -> ControlDetailOut:
    mapping_result = await db.execute(
        select(Requirement, Framework)
        .join(ControlRequirementLink, ControlRequirementLink.requirement_id == Requirement.id)
        .join(Framework, Framework.id == Requirement.framework_id)
        .where(ControlRequirementLink.control_id == control.id)
    )
    requirements = [
        RequirementMappingOut(
            requirement_id=req.id, requirement_key=req.key, requirement_name=req.name,
            framework_key=fw.key, framework_name=fw.name,
        )
        for req, fw in mapping_result.all()
    ]

    evidence_result = await db.execute(
        select(Evidence)
        .join(EvidenceControlLink, EvidenceControlLink.evidence_id == Evidence.id)
        .where(EvidenceControlLink.control_id == control.id)
    )
    evidence = [
        ControlEvidenceOut(id=e.id, name=e.name, status=effective_status(e.status, e.expires_at).value)
        for e in evidence_result.scalars().all()
    ]

    return ControlDetailOut(
        **ControlListItemOut.model_validate(control).model_dump(),
        description=control.description,
        objective=control.objective,
        testing_frequency=control.testing_frequency,
        last_tested_at=control.last_tested_at,
        requirements=requirements,
        evidence=evidence,
    )


@router.get("/{control_id}", response_model=ControlDetailOut)
async def get_control(
    org_id: uuid.UUID,
    control_id: uuid.UUID,
    ctx: OrgContext = Depends(require_org_role(Role.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    control = await db.get(Control, control_id)
    if control is None or control.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Control not found")
    return await _load_detail(control, db)


@router.patch("/{control_id}", response_model=ControlDetailOut)
async def update_control(
    org_id: uuid.UUID,
    control_id: uuid.UUID,
    payload: ControlUpdateRequest,
    request: Request,
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    control = await db.get(Control, control_id)
    if control is None or control.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Control not found")

    before_state = {
        "status": control.status.value,
        "owner_user_id": str(control.owner_user_id) if control.owner_user_id else None,
    }

    changed = False
    if payload.status is not None and payload.status != control.status:
        control.status = payload.status
        changed = True
    if payload.owner_user_id is not None and payload.owner_user_id != control.owner_user_id:
        control.owner_user_id = payload.owner_user_id
        changed = True
    if payload.next_review_at is not None:
        control.next_review_at = payload.next_review_at
        changed = True

    if changed:
        after_state = {
            "status": control.status.value,
            "owner_user_id": str(control.owner_user_id) if control.owner_user_id else None,
        }
        await write_audit_event(
            db,
            organization_id=org_id,
            actor_user_id=ctx.user.id,
            action="control.updated",
            resource_type="control",
            resource_id=str(control.id),
            before_state=before_state,
            after_state=after_state,
            request=request,
        )

    await db.commit()
    await db.refresh(control)
    return await _load_detail(control, db)
