"""The global framework/requirement catalog. Every entry here is sourced
from the framework's own published structure — not invented — because a
compliance tool that gets the requirements wrong is worse than one that
has fewer of them. Sources are noted per framework below.

Requirement granularity is kept consistent across frameworks: top-level
structural sections (SOC 2's CC-series, ISO 27001's four Annex A themes,
GDPR's named articles, PCI DSS's 12 requirements, HIPAA's safeguard
standards, NIST CSF's six functions) rather than every sub-clause — the
same level Control objects are meant to map against.

Adding a framework here does not touch any org's data: Framework and
Requirement are a shared, global catalog (see app/models/framework.py);
orgs opt in via OrganizationFramework. Safe to run repeatedly.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.framework import Framework, Requirement

# (framework_key, framework_name, framework_description, [(req_key, req_name), ...])
CATALOG: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    (
        "soc2",
        "SOC 2",
        "AICPA Trust Services Criteria — Security (Common Criteria) category",
        [
            ("CC1", "Control Environment"),
            ("CC2", "Information and Communication"),
            ("CC3", "Risk Assessment"),
            ("CC4", "Monitoring Activities"),
            ("CC5", "Control Activities"),
            ("CC6", "Logical and Physical Access Controls"),
            ("CC7", "System Operations"),
            ("CC8", "Change Management"),
            ("CC9", "Risk Mitigation"),
        ],
    ),
    (
        "iso27001",
        "ISO 27001",
        "ISO/IEC 27001:2022 — Annex A, four control themes (93 controls total)",
        [
            ("A.5", "Organizational controls"),
            ("A.6", "People controls"),
            ("A.7", "Physical controls"),
            ("A.8", "Technological controls"),
        ],
    ),
    (
        "gdpr",
        "GDPR",
        "EU General Data Protection Regulation (Regulation (EU) 2016/679) — key accountability and "
        "security articles",
        [
            ("Art.5", "Principles relating to processing of personal data"),
            ("Art.24", "Responsibility of the controller"),
            ("Art.25", "Data protection by design and by default"),
            ("Art.28", "Processor"),
            ("Art.30", "Records of processing activities"),
            ("Art.32", "Security of processing"),
            ("Art.33", "Notification of a personal data breach to the supervisory authority"),
            ("Art.34", "Communication of a personal data breach to the data subject"),
            ("Art.35", "Data protection impact assessment"),
        ],
    ),
    (
        "pci-dss-v4",
        "PCI DSS v4.0",
        "Payment Card Industry Data Security Standard, version 4.0 — 12 requirements",
        [
            ("Req.1", "Install and Maintain Network Security Controls"),
            ("Req.2", "Apply Secure Configurations to All System Components"),
            ("Req.3", "Protect Stored Account Data"),
            ("Req.4", "Protect Cardholder Data with Strong Cryptography During Transmission"),
            ("Req.5", "Protect All Systems and Networks from Malicious Software"),
            ("Req.6", "Develop and Maintain Secure Systems and Software"),
            ("Req.7", "Restrict Access to System Components and Cardholder Data by Business Need to Know"),
            ("Req.8", "Identify Users and Authenticate Access to System Components"),
            ("Req.9", "Restrict Physical Access to Cardholder Data"),
            ("Req.10", "Log and Monitor All Access to System Components and Cardholder Data"),
            ("Req.11", "Test Security of Systems and Networks Regularly"),
            ("Req.12", "Support Information Security with Organizational Policies and Programs"),
        ],
    ),
    (
        "hipaa",
        "HIPAA Security Rule",
        "HHS 45 CFR Part 164, Subpart C — administrative, physical, and technical safeguard standards",
        [
            ("164.308(a)(1)", "Security Management Process"),
            ("164.308(a)(3)", "Workforce Security"),
            ("164.308(a)(4)", "Information Access Management"),
            ("164.308(a)(5)", "Security Awareness and Training"),
            ("164.308(a)(6)", "Security Incident Procedures"),
            ("164.308(a)(7)", "Contingency Plan"),
            ("164.310(a)", "Facility Access Controls"),
            ("164.310(b)", "Workstation Use and Security"),
            ("164.310(d)", "Device and Media Controls"),
            ("164.312(a)", "Access Control"),
            ("164.312(b)", "Audit Controls"),
            ("164.312(c)", "Integrity"),
            ("164.312(e)", "Transmission Security"),
        ],
    ),
    (
        "nist-csf-2",
        "NIST CSF 2.0",
        "NIST Cybersecurity Framework, version 2.0 — six core functions",
        [
            ("GV", "Govern"),
            ("ID", "Identify"),
            ("PR", "Protect"),
            ("DE", "Detect"),
            ("RS", "Respond"),
            ("RC", "Recover"),
        ],
    ),
]


async def ensure_catalog_seeded(db: AsyncSession) -> dict[str, Framework]:
    """Idempotent: get-or-creates every framework and requirement in
    CATALOG. Returns {framework_key: Framework} for callers (like the
    demo seed script) that need to link controls against them."""
    frameworks: dict[str, Framework] = {}

    for key, name, description, requirements in CATALOG:
        result = await db.execute(select(Framework).where(Framework.key == key))
        framework = result.scalar_one_or_none()
        if framework is None:
            framework = Framework(key=key, name=name, description=description)
            db.add(framework)
            await db.flush()
        frameworks[key] = framework

        for req_key, req_name in requirements:
            req_result = await db.execute(
                select(Requirement).where(Requirement.framework_id == framework.id, Requirement.key == req_key)
            )
            if req_result.scalar_one_or_none() is None:
                db.add(
                    Requirement(
                        framework_id=framework.id,
                        key=req_key,
                        name=req_name,
                        description=f"{req_key} — {req_name}",
                    )
                )
        await db.flush()

    return frameworks
