"""Real AWS API calls that back automated controls, via boto3. boto3 is
synchronous, so every call runs in a worker thread (asyncio.to_thread)
rather than blocking the event loop — the same "no finding without a
citable source" discipline as the GitHub connector: every CheckResult
carries the exact API response that produced its verdict.

credentials shape: {"access_key_id": "...", "secret_access_key": "...",
"region": "us-east-1" (optional, defaults to us-east-1)}

A check never returns FAIL on an error it can't attribute to the control
(permission denied, resource missing, network error) — those come back
as NEEDS_REVIEW.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.models.control import ControlStatus
from app.services.connectors.base import CheckResult, ConnectorAuthError


def _client(credentials: dict, service: str):
    return boto3.client(
        service,
        aws_access_key_id=credentials.get("access_key_id"),
        aws_secret_access_key=credentials.get("secret_access_key"),
        region_name=credentials.get("region") or "us-east-1",
    )


def _error_message(exc: ClientError) -> str:
    return exc.response.get("Error", {}).get("Message", str(exc))


def _error_code(exc: ClientError) -> str:
    return exc.response.get("Error", {}).get("Code", "")


async def validate(credentials: dict) -> str:
    """Confirms the access key pair actually authenticates, and returns
    the AWS account ID for display."""

    def _call():
        return _client(credentials, "sts").get_caller_identity()

    try:
        identity = await asyncio.to_thread(_call)
    except NoCredentialsError:
        raise ConnectorAuthError("AWS access key ID and secret access key are required")
    except ClientError as exc:
        raise ConnectorAuthError(f"AWS rejected these credentials: {_error_message(exc)}")
    return f"AWS account {identity['Account']}"


async def check_root_mfa_enabled(credentials: dict, target: str) -> CheckResult:
    """Account-wide — target is unused but required for interface
    consistency with provider-agnostic binding."""

    def _call():
        return _client(credentials, "iam").get_account_summary()["SummaryMap"]

    try:
        summary = await asyncio.to_thread(_call)
    except ClientError as exc:
        return CheckResult(
            ControlStatus.NEEDS_REVIEW, f"Could not read account summary: {_error_message(exc)}", {"error": str(exc)}
        )
    enabled = summary.get("AccountMFAEnabled") == 1
    if enabled:
        return CheckResult(ControlStatus.PASS, "MFA is enabled on the AWS root account", summary)
    return CheckResult(ControlStatus.FAIL, "MFA is NOT enabled on the AWS root account", summary)


async def check_iam_users_mfa_enforced(credentials: dict, target: str) -> CheckResult:
    """Account-wide — target is unused."""

    def _call():
        iam = _client(credentials, "iam")
        users = iam.list_users()["Users"]
        without_mfa = [u["UserName"] for u in users if not iam.list_mfa_devices(UserName=u["UserName"])["MFADevices"]]
        return users, without_mfa

    try:
        users, without_mfa = await asyncio.to_thread(_call)
    except ClientError as exc:
        return CheckResult(
            ControlStatus.NEEDS_REVIEW, f"Could not list IAM users: {_error_message(exc)}", {"error": str(exc)}
        )
    if not users:
        return CheckResult(ControlStatus.NEEDS_REVIEW, "No IAM users found in this account", {"user_count": 0})
    if without_mfa:
        return CheckResult(
            ControlStatus.FAIL,
            f"{len(without_mfa)} of {len(users)} IAM users have no MFA device: {', '.join(without_mfa)}",
            {"user_count": len(users), "users_without_mfa": without_mfa},
        )
    return CheckResult(ControlStatus.PASS, f"All {len(users)} IAM users have an MFA device enrolled", {"user_count": len(users)})


async def check_cloudtrail_enabled(credentials: dict, target: str) -> CheckResult:
    """target: an AWS region, e.g. 'us-east-1'."""
    region = target or credentials.get("region") or "us-east-1"

    def _call():
        ct = _client({**credentials, "region": region}, "cloudtrail")
        trails = ct.describe_trails(includeShadowTrails=True)["trailList"]
        statuses = []
        for t in trails:
            status = ct.get_trail_status(Name=t["TrailARN"])
            statuses.append(
                {"name": t["Name"], "is_logging": status.get("IsLogging", False), "multi_region": t.get("IsMultiRegionTrail", False)}
            )
        return statuses

    try:
        statuses = await asyncio.to_thread(_call)
    except ClientError as exc:
        return CheckResult(
            ControlStatus.NEEDS_REVIEW, f"Could not read CloudTrail status: {_error_message(exc)}", {"error": str(exc)}
        )
    logging_trails = [s for s in statuses if s["is_logging"]]
    if logging_trails:
        return CheckResult(
            ControlStatus.PASS, f"{len(logging_trails)} CloudTrail trail(s) actively logging (region: {region})", {"trails": statuses}
        )
    return CheckResult(ControlStatus.FAIL, f"No CloudTrail trail is actively logging (region: {region})", {"trails": statuses})


async def check_s3_bucket_not_public(credentials: dict, target: str) -> CheckResult:
    """target: an S3 bucket name."""

    def _call():
        return _client(credentials, "s3").get_public_access_block(Bucket=target)["PublicAccessBlockConfiguration"]

    try:
        config = await asyncio.to_thread(_call)
    except ClientError as exc:
        code = _error_code(exc)
        if code == "NoSuchPublicAccessBlockConfiguration":
            return CheckResult(
                ControlStatus.FAIL, f"Bucket {target} has no S3 Block Public Access configuration", {"code": code}
            )
        return CheckResult(
            ControlStatus.NEEDS_REVIEW, f"Could not read public-access settings for {target}: {_error_message(exc)}", {"error": str(exc)}
        )
    if all(config.values()):
        return CheckResult(ControlStatus.PASS, f"Bucket {target} blocks all forms of public access", config)
    return CheckResult(ControlStatus.FAIL, f"Bucket {target} does not block all forms of public access", config)


CheckFn = Callable[[dict, str], Awaitable[CheckResult]]

CHECKS: dict[str, CheckFn] = {
    "aws.root_mfa_enabled": check_root_mfa_enabled,
    "aws.iam_users_mfa_enforced": check_iam_users_mfa_enforced,
    "aws.cloudtrail_enabled": check_cloudtrail_enabled,
    "aws.s3_bucket_not_public": check_s3_bucket_not_public,
}

CHECK_LABELS: dict[str, str] = {
    "aws.root_mfa_enabled": "Root account MFA enabled (target: ignored, e.g. \"account\")",
    "aws.iam_users_mfa_enforced": "All IAM users have MFA (target: ignored, e.g. \"account\")",
    "aws.cloudtrail_enabled": "CloudTrail logging enabled (target: region)",
    "aws.s3_bucket_not_public": "S3 bucket blocks public access (target: bucket name)",
}
