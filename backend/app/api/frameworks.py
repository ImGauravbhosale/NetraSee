from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, require_org_role
from app.core.db import get_db
from app.models.control import Control, ControlRequirementLink, ControlStatus
from app.models.framework import Framework, OrganizationFramework, Requirement
from app.models.membership import Role
from app.schemas.framework import AdoptedFrameworkOut, FrameworkOut, RequirementOut

router = APIRouter(prefix="/api/v1", tags=["frameworks"])


@router.get("/frameworks", response_model=list[FrameworkOut])
async def list_catalog(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Framework).order_by(Framework.name))
    return [FrameworkOut.model_validate(f) for f in result.scalars().all()]


@router.get("/orgs/{org_id}/frameworks", response_model=list[AdoptedFrameworkOut])
async def list_adopted(org_id: uuid.UUID, ctx: OrgContext = Depends(require_org_role(Role.VIEWER)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OrganizationFramework, Framework)
        .join(Framework, Framework.id == OrganizationFramework.framework_id)
        .where(OrganizationFramework.organization_id == org_id)
    )
    rows = result.all()

    out: list[AdoptedFrameworkOut] = []
    for org_framework, framework in rows:
        req_result = await db.execute(select(Requirement).where(Requirement.framework_id == framework.id))
        requirements = req_result.scalars().all()

        requirement_outs: list[RequirementOut] = []
        total_controls = 0
        total_passing = 0
        for req in requirements:
            link_result = await db.execute(
                select(Control)
                .join(ControlRequirementLink, ControlRequirementLink.control_id == Control.id)
                .where(ControlRequirementLink.requirement_id == req.id, Control.organization_id == org_id)
            )
            controls = link_result.scalars().all()
            passing = sum(1 for c in controls if c.status == ControlStatus.PASS)
            total_controls += len(controls)
            total_passing += passing
            requirement_outs.append(
                RequirementOut(
                    id=req.id, key=req.key, name=req.name, description=req.description,
                    control_count=len(controls), passing_count=passing,
                )
            )

        progress = (total_passing / total_controls * 100) if total_controls else 0.0
        out.append(
            AdoptedFrameworkOut(
                framework=FrameworkOut.model_validate(framework),
                adopted_at=org_framework.adopted_at.isoformat(),
                progress_percent=round(progress, 1),
                requirements=requirement_outs,
            )
        )
    return out


@router.post("/orgs/{org_id}/frameworks/{framework_id}/adopt", status_code=status.HTTP_201_CREATED)
async def adopt_framework(
    org_id: uuid.UUID,
    framework_id: uuid.UUID,
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    framework = await db.get(Framework, framework_id)
    if framework is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Framework not found")

    existing = await db.execute(
        select(OrganizationFramework).where(
            OrganizationFramework.organization_id == org_id,
            OrganizationFramework.framework_id == framework_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Framework already adopted")

    db.add(OrganizationFramework(organization_id=org_id, framework_id=framework_id))
    await db.commit()
    return {"ok": True}
