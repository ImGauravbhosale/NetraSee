from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.evidence import EvidenceStatus

EXPIRING_SOON_WINDOW = timedelta(days=14)


def effective_status(
    stored_status: EvidenceStatus, expires_at: datetime | None, *, now: datetime | None = None
) -> EvidenceStatus:
    """VALID/EXPIRING/EXPIRED is derived from `expires_at` at read time,
    not decided once at upload and left to go stale — v1 has no
    background worker to periodically flip a stored value, so every list/
    detail/dashboard read recomputes it fresh instead. UNDER_REVIEW is the
    one genuinely manual state (a human put it there) and is never
    overridden by a date computation."""
    if stored_status == EvidenceStatus.UNDER_REVIEW:
        return EvidenceStatus.UNDER_REVIEW
    if expires_at is None:
        return EvidenceStatus.VALID
    now = now or datetime.now(timezone.utc)
    if expires_at < now:
        return EvidenceStatus.EXPIRED
    if expires_at - now <= EXPIRING_SOON_WINDOW:
        return EvidenceStatus.EXPIRING
    return EvidenceStatus.VALID
