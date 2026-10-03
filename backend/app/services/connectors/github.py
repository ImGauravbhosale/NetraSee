"""Real GitHub API calls that back automated controls. Every check
returns a CheckResult carrying the exact API response that produced its
verdict — the same "no finding without a citable source" discipline the
rest of this project holds itself to, just pointed at a live account
instead of a code graph.

A check never returns FAIL on an error it can't actually attribute to the
control (auth failure, missing permission, network error, resource not
found) — those come back as NEEDS_REVIEW so a connectivity problem can
never silently read as "your security control is broken."

credentials shape: {"token": "<personal access token>"}
"""
from __future__ import annotations

from typing import Awaitable, Callable

import httpx

from app.core.config import settings
from app.models.control import ControlStatus
from app.services.connectors.base import CheckResult, ConnectorAuthError

GithubAuthError = ConnectorAuthError  # kept as a name consumers/tests already use

_HEADERS_BASE = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def validate(credentials: dict) -> str:
    """Confirms a PAT actually authenticates before a Connection is ever
    stored, and returns the authenticated login for display."""
    token = credentials.get("token", "")
    async with httpx.AsyncClient(base_url=settings.github_api_base_url, timeout=10.0) as client:
        resp = await client.get("/user", headers={**_HEADERS_BASE, "Authorization": f"Bearer {token}"})
    if resp.status_code == 401:
        raise ConnectorAuthError("GitHub rejected this token — check it hasn't expired or been revoked")
    resp.raise_for_status()
    return resp.json()["login"]


async def _get(client: httpx.AsyncClient, path: str, token: str) -> httpx.Response:
    return await client.get(path, headers={**_HEADERS_BASE, "Authorization": f"Bearer {token}"})


async def check_branch_protection(credentials: dict, target: str) -> CheckResult:
    """target: 'owner/repo'. PASS only if the default branch requires
    pull request reviews before merging — a branch can be "protected" in
    GitHub's terms while still allowing direct pushes to main, so
    protection alone isn't the bar."""
    token = credentials.get("token", "")
    async with httpx.AsyncClient(base_url=settings.github_api_base_url, timeout=10.0) as client:
        repo_resp = await _get(client, f"/repos/{target}", token)
        if repo_resp.status_code == 404:
            return CheckResult(
                ControlStatus.NEEDS_REVIEW,
                f"Repository {target} not found or not accessible with this token",
                {"status_code": 404},
            )
        repo_resp.raise_for_status()
        default_branch = repo_resp.json()["default_branch"]

        protection_resp = await _get(client, f"/repos/{target}/branches/{default_branch}/protection", token)

    if protection_resp.status_code == 404:
        return CheckResult(
            ControlStatus.FAIL,
            f"Branch '{default_branch}' on {target} has no protection rules configured",
            {"default_branch": default_branch, "protected": False},
        )
    if protection_resp.status_code == 403:
        return CheckResult(
            ControlStatus.NEEDS_REVIEW,
            "Token lacks permission to read branch protection (needs repo admin access)",
            {"status_code": 403},
        )
    protection_resp.raise_for_status()
    data = protection_resp.json()
    requires_reviews = bool(data.get("required_pull_request_reviews"))
    if requires_reviews:
        return CheckResult(
            ControlStatus.PASS,
            f"Branch '{default_branch}' on {target} requires pull request reviews before merging",
            data,
        )
    return CheckResult(
        ControlStatus.FAIL,
        f"Branch '{default_branch}' on {target} is protected but does not require pull request reviews",
        data,
    )


async def check_org_2fa_enforced(credentials: dict, target: str) -> CheckResult:
    """target: a GitHub org login (no repo)."""
    token = credentials.get("token", "")
    async with httpx.AsyncClient(base_url=settings.github_api_base_url, timeout=10.0) as client:
        resp = await _get(client, f"/orgs/{target}", token)
    if resp.status_code == 404:
        return CheckResult(
            ControlStatus.NEEDS_REVIEW,
            f"Organization {target} not found or not accessible with this token",
            {"status_code": 404},
        )
    resp.raise_for_status()
    data = resp.json()
    enforced = data.get("two_factor_requirement_enabled")
    if enforced is None:
        return CheckResult(
            ControlStatus.NEEDS_REVIEW,
            "GitHub did not report 2FA enforcement status — token may need org admin access",
            data,
        )
    if enforced:
        return CheckResult(
            ControlStatus.PASS, f"Two-factor authentication is required for all members of {target}", data
        )
    return CheckResult(
        ControlStatus.FAIL, f"Two-factor authentication is NOT required for members of {target}", data
    )


async def check_dependabot_alerts(credentials: dict, target: str) -> CheckResult:
    """target: 'owner/repo'. This endpoint has no response body — GitHub
    signals the setting purely via status code."""
    token = credentials.get("token", "")
    async with httpx.AsyncClient(base_url=settings.github_api_base_url, timeout=10.0) as client:
        resp = await _get(client, f"/repos/{target}/vulnerability-alerts", token)
    if resp.status_code == 204:
        return CheckResult(ControlStatus.PASS, f"Dependabot alerts are enabled on {target}", {"enabled": True})
    if resp.status_code == 404:
        return CheckResult(ControlStatus.FAIL, f"Dependabot alerts are NOT enabled on {target}", {"enabled": False})
    if resp.status_code == 403:
        return CheckResult(
            ControlStatus.NEEDS_REVIEW, "Token lacks permission to read vulnerability alert settings", {"status_code": 403}
        )
    resp.raise_for_status()
    return CheckResult(
        ControlStatus.NEEDS_REVIEW,
        f"Unexpected response ({resp.status_code}) checking Dependabot alerts",
        {"status_code": resp.status_code},
    )


async def check_secret_scanning(credentials: dict, target: str) -> CheckResult:
    """target: 'owner/repo'. Secret scanning status is only visible to a
    token with admin access on the repo, and only meaningful on repos
    where GitHub Advanced Security applies."""
    token = credentials.get("token", "")
    async with httpx.AsyncClient(base_url=settings.github_api_base_url, timeout=10.0) as client:
        resp = await _get(client, f"/repos/{target}", token)
    if resp.status_code == 404:
        return CheckResult(
            ControlStatus.NEEDS_REVIEW,
            f"Repository {target} not found or not accessible with this token",
            {"status_code": 404},
        )
    resp.raise_for_status()
    data = resp.json()
    analysis = data.get("security_and_analysis") or {}
    status = (analysis.get("secret_scanning") or {}).get("status")
    if status is None:
        return CheckResult(
            ControlStatus.NEEDS_REVIEW,
            "GitHub did not report secret scanning status for this repository "
            "(needs an admin token on the repo)",
            data,
        )
    if status == "enabled":
        return CheckResult(ControlStatus.PASS, f"Secret scanning is enabled on {target}", analysis)
    return CheckResult(ControlStatus.FAIL, f"Secret scanning is NOT enabled on {target}", analysis)


CheckFn = Callable[[dict, str], Awaitable[CheckResult]]

CHECKS: dict[str, CheckFn] = {
    "github.branch_protection": check_branch_protection,
    "github.org_2fa_enforced": check_org_2fa_enforced,
    "github.dependabot_alerts": check_dependabot_alerts,
    "github.secret_scanning": check_secret_scanning,
}

CHECK_LABELS: dict[str, str] = {
    "github.branch_protection": "Branch protection requires PR reviews (target: owner/repo)",
    "github.org_2fa_enforced": "Org-wide 2FA enforcement (target: org login)",
    "github.dependabot_alerts": "Dependabot alerts enabled (target: owner/repo)",
    "github.secret_scanning": "Secret scanning enabled (target: owner/repo)",
}
