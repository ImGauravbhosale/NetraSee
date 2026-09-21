from datetime import datetime, timedelta, timezone

from app.models.evidence import EvidenceStatus
from app.services.evidence_status import effective_status

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_no_expiry_is_valid():
    assert effective_status(EvidenceStatus.VALID, None, now=NOW) == EvidenceStatus.VALID


def test_far_future_expiry_is_valid():
    assert effective_status(EvidenceStatus.VALID, NOW + timedelta(days=90), now=NOW) == EvidenceStatus.VALID


def test_within_window_is_expiring():
    assert effective_status(EvidenceStatus.VALID, NOW + timedelta(days=5), now=NOW) == EvidenceStatus.EXPIRING


def test_past_expiry_is_expired():
    assert effective_status(EvidenceStatus.VALID, NOW - timedelta(days=1), now=NOW) == EvidenceStatus.EXPIRED


def test_under_review_overrides_date_computation_even_when_expired():
    assert (
        effective_status(EvidenceStatus.UNDER_REVIEW, NOW - timedelta(days=100), now=NOW)
        == EvidenceStatus.UNDER_REVIEW
    )
