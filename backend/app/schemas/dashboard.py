from __future__ import annotations

from pydantic import BaseModel


class FrameworkProgress(BaseModel):
    framework_key: str
    framework_name: str
    progress_percent: float
    control_count: int
    passing_count: int


class ControlCounts(BaseModel):
    passing: int
    failing: int
    needs_review: int
    not_applicable: int
    not_tested: int


class EvidenceCounts(BaseModel):
    valid: int
    expiring: int
    expired: int
    under_review: int


class DashboardOut(BaseModel):
    frameworks: list[FrameworkProgress]
    controls: ControlCounts
    evidence: EvidenceCounts
