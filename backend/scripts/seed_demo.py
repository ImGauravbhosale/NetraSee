"""Populates a demo organization with SOC 2 + ISO 27001 adopted, controls
in a mix of statuses, and evidence in a mix of statuses — including at
least one control mapped to BOTH frameworks, since that reusability claim
should be demonstrable, not just asserted in docs.

Usage: uv run python scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.core.db import async_session_factory
from app.core.security import hash_password
from app.models.control import AutomationStatus, Control, ControlRequirementLink, ControlStatus
from app.models.evidence import Evidence, EvidenceControlLink
from app.models.framework import Framework, OrganizationFramework, Requirement
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.user import User

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "netrasee-demo-1234"


async def _get_or_create_framework(db, key: str, name: str, description: str) -> Framework:
    result = await db.execute(select(Framework).where(Framework.key == key))
    framework = result.scalar_one_or_none()
    if framework is None:
        framework = Framework(key=key, name=name, description=description)
        db.add(framework)
        await db.flush()
    return framework


async def _get_or_create_requirement(db, framework: Framework, key: str, name: str) -> Requirement:
    result = await db.execute(
        select(Requirement).where(Requirement.framework_id == framework.id, Requirement.key == key)
    )
    req = result.scalar_one_or_none()
    if req is None:
        req = Requirement(framework_id=framework.id, key=key, name=name, description=f"{key} — {name}")
        db.add(req)
        await db.flush()
    return req


def _fake_checksum(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


async def seed() -> None:
    async with async_session_factory() as db:
        existing = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        if existing.scalar_one_or_none() is not None:
            print("Demo data already exists — skipping.")
            return

        org = Organization(name="Netrasee Demo Co.")
        owner = User(email=DEMO_EMAIL, name="Demo Owner", hashed_password=hash_password(DEMO_PASSWORD))
        db.add_all([org, owner])
        await db.flush()
        db.add(Membership(user_id=owner.id, organization_id=org.id, role=Role.OWNER))

        soc2 = await _get_or_create_framework(db, "soc2", "SOC 2", "AICPA Trust Services Criteria")
        iso = await _get_or_create_framework(db, "iso27001", "ISO 27001", "Information security management")

        db.add(OrganizationFramework(organization_id=org.id, framework_id=soc2.id))
        db.add(OrganizationFramework(organization_id=org.id, framework_id=iso.id))

        cc6 = await _get_or_create_requirement(db, soc2, "CC6", "Logical and Physical Access Controls")
        cc7 = await _get_or_create_requirement(db, soc2, "CC7", "System Operations")
        a5 = await _get_or_create_requirement(db, iso, "A.5", "Organizational controls")
        a8 = await _get_or_create_requirement(db, iso, "A.8", "Technological controls")

        now = datetime.now(timezone.utc)

        # The control that proves reusability: one row, mapped to two
        # requirements in two different frameworks.
        mfa_control = Control(
            organization_id=org.id,
            control_key="CTRL-001",
            name="MFA is enforced for privileged accounts",
            description="All accounts with administrative or privileged access require multi-factor authentication.",
            objective="Prevent unauthorized access to privileged accounts via credential compromise alone.",
            owner_user_id=owner.id,
            category="Access Control",
            status=ControlStatus.PASS,
            automation_status=AutomationStatus.MANUAL,
            testing_frequency="quarterly",
            last_tested_at=now - timedelta(days=10),
            next_review_at=now + timedelta(days=80),
        )
        logging_control = Control(
            organization_id=org.id,
            control_key="CTRL-002",
            name="Centralized audit logging is enabled for production systems",
            description="All production systems ship logs to a centralized, tamper-evident store.",
            objective="Ensure security-relevant events are recorded and retrievable for investigation.",
            owner_user_id=owner.id,
            category="Logging & Monitoring",
            status=ControlStatus.FAIL,
            automation_status=AutomationStatus.MANUAL,
            testing_frequency="quarterly",
            last_tested_at=now - timedelta(days=40),
            next_review_at=now + timedelta(days=5),
        )
        vuln_control = Control(
            organization_id=org.id,
            control_key="CTRL-003",
            name="Vulnerability scanning runs on a defined schedule",
            description="Automated vulnerability scans run at least weekly against production infrastructure.",
            objective="Detect known vulnerabilities before they're exploited.",
            owner_user_id=owner.id,
            category="Vulnerability Management",
            status=ControlStatus.NEEDS_REVIEW,
            automation_status=AutomationStatus.MANUAL,
            testing_frequency="monthly",
            last_tested_at=now - timedelta(days=95),
            next_review_at=now + timedelta(days=2),
        )
        offboarding_control = Control(
            organization_id=org.id,
            control_key="CTRL-004",
            name="Access is revoked within 24 hours of employee offboarding",
            description="Terminated employees' system access is removed within one business day.",
            objective="Limit the window an ex-employee could misuse retained access.",
            owner_user_id=owner.id,
            category="Access Control",
            status=ControlStatus.NOT_TESTED,
            automation_status=AutomationStatus.MANUAL,
            testing_frequency="quarterly",
        )

        db.add_all([mfa_control, logging_control, vuln_control, offboarding_control])
        await db.flush()

        db.add_all(
            [
                ControlRequirementLink(control_id=mfa_control.id, requirement_id=cc6.id),
                ControlRequirementLink(control_id=mfa_control.id, requirement_id=a8.id),
                ControlRequirementLink(control_id=logging_control.id, requirement_id=cc7.id),
                ControlRequirementLink(control_id=logging_control.id, requirement_id=a8.id),
                ControlRequirementLink(control_id=vuln_control.id, requirement_id=cc7.id),
                ControlRequirementLink(control_id=offboarding_control.id, requirement_id=cc6.id),
                ControlRequirementLink(control_id=offboarding_control.id, requirement_id=a5.id),
            ]
        )

        evidence_dir = Path(settings.evidence_storage_dir) / str(org.id)
        evidence_dir.mkdir(parents=True, exist_ok=True)

        valid_evidence = Evidence(
            organization_id=org.id,
            name="Okta MFA policy screenshot",
            description="Screenshot of the org-wide MFA enforcement policy in the Okta admin console.",
            source="manual",
            collected_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=80),
            owner_user_id=owner.id,
            status="VALID",
            checksum_sha256=_fake_checksum("okta-mfa-policy"),
            collection_method="manual_upload",
            file_path=str(evidence_dir / "seed-placeholder-mfa.txt"),
        )
        expiring_evidence = Evidence(
            organization_id=org.id,
            name="Q2 access review sign-off",
            description="Signed attestation from IT confirming quarterly access review was completed.",
            source="manual",
            collected_at=now - timedelta(days=75),
            expires_at=now + timedelta(days=10),
            owner_user_id=owner.id,
            status="VALID",
            checksum_sha256=_fake_checksum("q2-access-review"),
            collection_method="manual_upload",
            file_path=str(evidence_dir / "seed-placeholder-access-review.txt"),
        )
        expired_evidence = Evidence(
            organization_id=org.id,
            name="Centralized logging configuration export",
            description="Export of the log-shipping configuration from the previous quarter.",
            source="manual",
            collected_at=now - timedelta(days=200),
            expires_at=now - timedelta(days=20),
            owner_user_id=owner.id,
            status="VALID",
            checksum_sha256=_fake_checksum("logging-config-old"),
            collection_method="manual_upload",
            file_path=str(evidence_dir / "seed-placeholder-logging.txt"),
        )

        for e in (valid_evidence, expiring_evidence, expired_evidence):
            (Path(e.file_path)).write_text(f"Seed placeholder for: {e.name}\n")

        db.add_all([valid_evidence, expiring_evidence, expired_evidence])
        await db.flush()

        db.add_all(
            [
                EvidenceControlLink(evidence_id=valid_evidence.id, control_id=mfa_control.id),
                EvidenceControlLink(evidence_id=expiring_evidence.id, control_id=offboarding_control.id),
                EvidenceControlLink(evidence_id=expired_evidence.id, control_id=logging_control.id),
            ]
        )

        await db.commit()
        print(f"Seeded demo org {org.id} — login as {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
