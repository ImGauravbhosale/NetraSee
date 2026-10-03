"""Shared types every connector module implements, so automation.py and
the API layer can dispatch by provider without knowing connector-specific
details. A connector module exposes:

    async def validate(credentials: dict) -> str   # returns account_login
    CHECKS: dict[str, Callable[[dict, str], Awaitable[CheckResult]]]
    CHECK_LABELS: dict[str, str]

`credentials` is whatever shape that provider needs (a single PAT for
GitHub, an access key pair for AWS) — stored as one JSON blob, encrypted,
in Connection.encrypted_token. `target` is also provider-specific
(`owner/repo` for GitHub, a bucket name or region for AWS).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.control import ControlStatus


@dataclass
class CheckResult:
    status: ControlStatus
    summary: str
    raw: dict


class ConnectorAuthError(ValueError):
    """Credentials were rejected by the provider itself — never raised
    for a permissions gap or a missing resource, which are NEEDS_REVIEW
    on the individual check, not an auth failure on the whole
    connection."""
