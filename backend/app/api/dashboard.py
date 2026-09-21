from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, require_org_role
from app.core.db import get_db
from app.models.control import Control, ControlRequirementLink, ControlStatus
from app.models.evidence import Evidence, EvidenceStatus
from app.models.framework import Framework, OrganizationFramework, Requirement
from app.models.membership import Role
from app.schemas.dashboard import ControlCounts, DashboardOut, EvidenceCounts, FrameworkProgress
from app.services.evidence_status import effective_status

router = APIRouter(prefix="/api/v1/orgs/{org_id}/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
async def get_dashboard(
    org_id: uuid.UUID, ctx: OrgContext = Depends(require_org_role(Role.VIEWER)), db: AsyncSession = Depends(get_db)
):
    controls_result = await db.execute(select(Control).where(Control.organization_id == org_id))
    controls = controls_result.scalars().all()

    control_counts = ControlCounts(
        passing=sum(1 for c in controls if c.status == ControlStatus.PASS),
        failing=sum(1 for c in controls if c.status == ControlStatus.FAIL),
        needs_review=sum(1 for c in controls if c.status == ControlStatus.NEEDS_REVIEW),
        not_applicable=sum(1 for c in controls if c.status == ControlStatus.NOT_APPLICABLE),
        not_tested=sum(1 for c in controls if c.status == ControlStatus.NOT_TESTED),
    )

    evidence_result = await db.execute(select(Evidence).where(Evidence.organization_id == org_id))
    evidence_rows = evidence_result.scalars().all()
    statuses = [effective_status(e.status, e.expires_at) for e in evidence_rows]
    evidence_counts = EvidenceCounts(
        valid=statuses.count(EvidenceStatus.VALID),
        expiring=statuses.count(EvidenceStatus.EXPIRING),
        expired=statuses.count(EvidenceStatus.EXPIRED),
        under_review=statuses.count(EvidenceStatus.UNDER_REVIEW),
    )

    adopted_result = await db.execute(
        select(OrganizationFramework, Framework)
        .join(Framework, Framework.id == OrganizationFramework.framework_id)
        .where(OrganizationFramework.organization_id == org_id)
    )
    framework_progress: list[FrameworkProgress] = []
    for _org_fw, framework in adopted_result.all():
        req_result = await db.execute(select(Requirement.id).where(Requirement.framework_id == framework.id))
        requirement_ids = [r for r in req_result.scalars().all()]

        if requirement_ids:
            fw_control_result = await db.execute(
                select(Control)
                .join(ControlRequirementLink, ControlRequirementLink.control_id == Control.id)
                .where(
                    ControlRequirementLink.requirement_id.in_(requirement_ids),
                    Control.organization_id == org_id,
                )
                .distinct()
            )
            fw_controls = fw_control_result.scalars().all()
        else:
            fw_controls = []

        fw_passing = sum(1 for c in fw_controls if c.status == ControlStatus.PASS)
        progress = (fw_passing / len(fw_controls) * 100) if fw_controls else 0.0
        framework_progress.append(
            FrameworkProgress(
                framework_key=framework.key,
                framework_name=framework.name,
                progress_percent=round(progress, 1),
                control_count=len(fw_controls),
                passing_count=fw_passing,
            )
        )

    return DashboardOut(frameworks=framework_progress, controls=control_counts, evidence=evidence_counts)
