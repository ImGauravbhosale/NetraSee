"""The CLI entry point for a single NetraSee check — the same connector
engine the web app uses (app.services.connectors), with no database, no
web server, and no Postgres required. This is what makes NetraSee usable
as a CI gate (see action.yml at the repo root) and not just a platform
you deploy: `uv run netrasee-check ...` runs one real check against a
live GitHub or AWS account and exits non-zero on a real finding.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from app.models.control import ControlStatus
from app.services.connectors import CONNECTORS, base


def _build_credentials(provider: str, args: argparse.Namespace) -> dict:
    if provider == "GITHUB":
        token = args.token or os.environ.get("NETRASEE_GITHUB_TOKEN")
        if not token:
            print("GitHub check requires --token or the NETRASEE_GITHUB_TOKEN env var", file=sys.stderr)
            sys.exit(2)
        return {"token": token}
    if provider == "AWS":
        access_key_id = args.access_key_id or os.environ.get("NETRASEE_AWS_ACCESS_KEY_ID")
        secret_access_key = args.secret_access_key or os.environ.get("NETRASEE_AWS_SECRET_ACCESS_KEY")
        region = args.region or os.environ.get("NETRASEE_AWS_REGION", "us-east-1")
        if not access_key_id or not secret_access_key:
            print(
                "AWS check requires --access-key-id/--secret-access-key or "
                "NETRASEE_AWS_ACCESS_KEY_ID/NETRASEE_AWS_SECRET_ACCESS_KEY",
                file=sys.stderr,
            )
            sys.exit(2)
        return {"access_key_id": access_key_id, "secret_access_key": secret_access_key, "region": region}
    print(f"Unknown provider: {provider}. Available: {', '.join(CONNECTORS)}", file=sys.stderr)
    sys.exit(2)


async def _run_check(args: argparse.Namespace) -> base.CheckResult:
    provider = args.provider.upper()
    connector = CONNECTORS.get(provider)
    if connector is None:
        print(f"Unknown provider: {provider}. Available: {', '.join(CONNECTORS)}", file=sys.stderr)
        sys.exit(2)

    check_fn = connector.CHECKS.get(args.check)
    if check_fn is None:
        print(f"Unknown check '{args.check}' for {provider}. Available checks:", file=sys.stderr)
        for key, label in connector.CHECK_LABELS.items():
            print(f"  {key} — {label}", file=sys.stderr)
        sys.exit(2)

    credentials = _build_credentials(provider, args)
    try:
        return await check_fn(credentials, args.target)
    except Exception as exc:  # noqa: BLE001 — a network/auth error is a CI result, not a crash
        return base.CheckResult(
            status=ControlStatus.NEEDS_REVIEW,
            summary=f"Check failed to run: {exc}",
            raw={"error": str(exc)},
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="netrasee-check",
        description="Run one NetraSee automated compliance check against a live GitHub or AWS "
        "account and exit non-zero if it doesn't pass — no database, no server, just the check.",
    )
    parser.add_argument("--provider", help="github or aws (omit with --list-checks to list every provider's checks)")
    parser.add_argument("--check", help="e.g. github.branch_protection, aws.root_mfa_enabled")
    parser.add_argument(
        "--target", help="owner/repo, org login, bucket name, or region, depending on the check"
    )
    parser.add_argument("--token", help="GitHub PAT (or set NETRASEE_GITHUB_TOKEN)")
    parser.add_argument("--access-key-id", help="AWS access key ID (or set NETRASEE_AWS_ACCESS_KEY_ID)")
    parser.add_argument("--secret-access-key", help="AWS secret access key (or set NETRASEE_AWS_SECRET_ACCESS_KEY)")
    parser.add_argument("--region", help="AWS region (or set NETRASEE_AWS_REGION, default us-east-1)")
    parser.add_argument("--json", action="store_true", help="Print the full result as JSON, not a one-line summary")
    parser.add_argument(
        "--fail-on-review",
        action="store_true",
        help="Also exit non-zero on NEEDS_REVIEW, not just FAIL — use in a CI gate that must not "
        "silently pass on an inconclusive check",
    )
    parser.add_argument("--list-checks", action="store_true", help="List available checks for --provider and exit")
    args = parser.parse_args()

    if args.list_checks:
        provider = args.provider.upper() if args.provider else None
        if provider and provider not in CONNECTORS:
            print(f"Unknown provider: {provider}. Available: {', '.join(CONNECTORS)}", file=sys.stderr)
            sys.exit(2)
        connectors = {provider: CONNECTORS[provider]} if provider else CONNECTORS
        for connector in connectors.values():
            for key, label in connector.CHECK_LABELS.items():
                print(f"{key}\t{label}")
        sys.exit(0)

    if not args.provider or not args.check or not args.target:
        parser.error("--provider, --check, and --target are required unless --list-checks is given")

    result = asyncio.run(_run_check(args))

    if args.json:
        print(json.dumps({"status": result.status.value, "summary": result.summary, "raw": result.raw}, indent=2, default=str))
    else:
        print(f"[{result.status.value}] {result.summary}")

    if result.status.value == "FAIL":
        sys.exit(1)
    if result.status.value == "NEEDS_REVIEW" and args.fail_on_review:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
