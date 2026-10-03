"""Tests for the CLI entry point — exit codes are the contract a CI gate
depends on, so they're tested explicitly rather than just trusting the
underlying check logic (already covered in test_connectors_github.py /
test_connectors_aws.py)."""
import sys

import pytest

from app import cli
from app.models.control import ControlStatus
from app.services.connectors import github
from app.services.connectors.base import CheckResult


def _run(monkeypatch, capsys, argv):
    monkeypatch.setattr(sys, "argv", ["netrasee-check", *argv])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    return exc_info.value.code, capsys.readouterr()


def test_list_checks_exits_zero(monkeypatch, capsys):
    code, out = _run(monkeypatch, capsys, ["--list-checks"])
    assert code == 0
    assert "github.branch_protection" in out.out
    assert "aws.root_mfa_enabled" in out.out


def test_missing_required_args_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["netrasee-check"])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 2


def test_unknown_check_exits_2(monkeypatch, capsys):
    code, out = _run(monkeypatch, capsys, ["--provider", "github", "--check", "github.nonexistent", "--target", "x", "--token", "t"])
    assert code == 2
    assert "Unknown check" in out.err


def test_missing_github_token_exits_2(monkeypatch, capsys):
    monkeypatch.delenv("NETRASEE_GITHUB_TOKEN", raising=False)
    code, out = _run(monkeypatch, capsys, ["--provider", "github", "--check", "github.branch_protection", "--target", "acme/widgets"])
    assert code == 2


def test_pass_exits_zero(monkeypatch, capsys):
    async def fake_check(credentials, target):
        return CheckResult(ControlStatus.PASS, "all good", {"ok": True})

    monkeypatch.setitem(github.CHECKS, "github.branch_protection", fake_check)
    code, out = _run(
        monkeypatch, capsys,
        ["--provider", "github", "--check", "github.branch_protection", "--target", "acme/widgets", "--token", "t"],
    )
    assert code == 0
    assert "[PASS]" in out.out


def test_fail_exits_one(monkeypatch, capsys):
    async def fake_check(credentials, target):
        return CheckResult(ControlStatus.FAIL, "not protected", {"ok": False})

    monkeypatch.setitem(github.CHECKS, "github.branch_protection", fake_check)
    code, out = _run(
        monkeypatch, capsys,
        ["--provider", "github", "--check", "github.branch_protection", "--target", "acme/widgets", "--token", "t"],
    )
    assert code == 1
    assert "[FAIL]" in out.out


def test_needs_review_exits_zero_by_default(monkeypatch, capsys):
    async def fake_check(credentials, target):
        return CheckResult(ControlStatus.NEEDS_REVIEW, "inconclusive", {})

    monkeypatch.setitem(github.CHECKS, "github.branch_protection", fake_check)
    code, out = _run(
        monkeypatch, capsys,
        ["--provider", "github", "--check", "github.branch_protection", "--target", "acme/widgets", "--token", "t"],
    )
    assert code == 0


def test_needs_review_exits_one_with_fail_on_review(monkeypatch, capsys):
    async def fake_check(credentials, target):
        return CheckResult(ControlStatus.NEEDS_REVIEW, "inconclusive", {})

    monkeypatch.setitem(github.CHECKS, "github.branch_protection", fake_check)
    code, out = _run(
        monkeypatch, capsys,
        ["--provider", "github", "--check", "github.branch_protection", "--target", "acme/widgets", "--token", "t", "--fail-on-review"],
    )
    assert code == 1


def test_an_unhandled_exception_becomes_needs_review_not_a_crash(monkeypatch, capsys):
    async def fake_check(credentials, target):
        raise RuntimeError("simulated network failure")

    monkeypatch.setitem(github.CHECKS, "github.branch_protection", fake_check)
    code, out = _run(
        monkeypatch, capsys,
        ["--provider", "github", "--check", "github.branch_protection", "--target", "acme/widgets", "--token", "t", "--json"],
    )
    assert code == 0  # NEEDS_REVIEW without --fail-on-review
    assert "NEEDS_REVIEW" in out.out
    assert "simulated network failure" in out.out


def test_json_output_is_valid_json(monkeypatch, capsys):
    import json

    async def fake_check(credentials, target):
        return CheckResult(ControlStatus.PASS, "all good", {"detail": "x"})

    monkeypatch.setitem(github.CHECKS, "github.branch_protection", fake_check)
    code, out = _run(
        monkeypatch, capsys,
        ["--provider", "github", "--check", "github.branch_protection", "--target", "acme/widgets", "--token", "t", "--json"],
    )
    parsed = json.loads(out.out)
    assert parsed["status"] == "PASS"
    assert parsed["raw"]["detail"] == "x"


def test_aws_check_requires_both_credential_fields(monkeypatch, capsys):
    monkeypatch.delenv("NETRASEE_AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("NETRASEE_AWS_SECRET_ACCESS_KEY", raising=False)
    code, out = _run(
        monkeypatch, capsys,
        ["--provider", "aws", "--check", "aws.root_mfa_enabled", "--target", "account", "--access-key-id", "AKIA123"],
    )
    assert code == 2
