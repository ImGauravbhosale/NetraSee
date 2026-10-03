"""Unit tests for the AWS connector against botocore's Stubber — which
validates requests against AWS's real service models and returns
responses shaped exactly like the real API, without any network call.
Verifies NetraSee's own PASS/FAIL/NEEDS_REVIEW mapping, not AWS's API."""
from datetime import datetime, timezone

import boto3
import pytest
from botocore.stub import Stubber

from app.models.control import ControlStatus
from app.services.connectors import aws as aws_connector

CREDS = {"access_key_id": "AKIAFAKEFAKEFAKEFAKE", "secret_access_key": "fakefakefakefakefakefakefakefakefakefake"}


def _stubbed(service: str, region: str = "us-east-1"):
    client = boto3.client(service, aws_access_key_id="x", aws_secret_access_key="y", region_name=region)
    return client, Stubber(client)


async def test_validate_returns_account_id(monkeypatch):
    client, stubber = _stubbed("sts")
    stubber.add_response(
        "get_caller_identity",
        {"Account": "123456789012", "UserId": "AIDAEXAMPLE", "Arn": "arn:aws:iam::123456789012:user/test"},
    )
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    login = await aws_connector.validate(CREDS)
    assert "123456789012" in login


async def test_validate_rejects_bad_credentials(monkeypatch):
    client, stubber = _stubbed("sts")
    stubber.add_client_error(
        "get_caller_identity",
        service_error_code="InvalidClientTokenId",
        service_message="The security token included in the request is invalid",
        http_status_code=403,
    )
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    with pytest.raises(aws_connector.ConnectorAuthError):
        await aws_connector.validate(CREDS)


async def test_root_mfa_pass_when_enabled(monkeypatch):
    client, stubber = _stubbed("iam")
    stubber.add_response("get_account_summary", {"SummaryMap": {"AccountMFAEnabled": 1}})
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    result = await aws_connector.check_root_mfa_enabled(CREDS, "account")
    assert result.status == ControlStatus.PASS


async def test_root_mfa_fail_when_disabled(monkeypatch):
    client, stubber = _stubbed("iam")
    stubber.add_response("get_account_summary", {"SummaryMap": {"AccountMFAEnabled": 0}})
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    result = await aws_connector.check_root_mfa_enabled(CREDS, "account")
    assert result.status == ControlStatus.FAIL


async def test_iam_users_mfa_fail_when_one_user_missing_mfa(monkeypatch):
    client, stubber = _stubbed("iam")
    user = {
        "UserName": "alice",
        "UserId": "AIDACKCEVSQ6C2EXAMPLE",
        "Arn": "arn:aws:iam::123456789012:user/alice",
        "Path": "/",
        "CreateDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    stubber.add_response("list_users", {"Users": [user]})
    stubber.add_response("list_mfa_devices", {"MFADevices": []}, expected_params={"UserName": "alice"})
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    result = await aws_connector.check_iam_users_mfa_enforced(CREDS, "account")
    assert result.status == ControlStatus.FAIL
    assert "alice" in result.summary


async def test_iam_users_mfa_pass_when_all_have_mfa(monkeypatch):
    client, stubber = _stubbed("iam")
    user = {
        "UserName": "bob",
        "UserId": "AIDACKCEVSQ6C2EXAMPL2",
        "Arn": "arn:aws:iam::123456789012:user/bob",
        "Path": "/",
        "CreateDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    stubber.add_response("list_users", {"Users": [user]})
    stubber.add_response(
        "list_mfa_devices",
        {"MFADevices": [{"UserName": "bob", "SerialNumber": "arn:aws:iam::123456789012:mfa/bob", "EnableDate": datetime(2024, 1, 1, tzinfo=timezone.utc)}]},
        expected_params={"UserName": "bob"},
    )
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    result = await aws_connector.check_iam_users_mfa_enforced(CREDS, "account")
    assert result.status == ControlStatus.PASS


async def test_cloudtrail_pass_when_logging(monkeypatch):
    client, stubber = _stubbed("cloudtrail")
    arn = "arn:aws:cloudtrail:us-east-1:123456789012:trail/main"
    stubber.add_response("describe_trails", {"trailList": [{"Name": "main", "TrailARN": arn, "IsMultiRegionTrail": True}]})
    stubber.add_response("get_trail_status", {"IsLogging": True}, expected_params={"Name": arn})
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    result = await aws_connector.check_cloudtrail_enabled(CREDS, "us-east-1")
    assert result.status == ControlStatus.PASS


async def test_cloudtrail_fail_when_no_trail(monkeypatch):
    client, stubber = _stubbed("cloudtrail")
    stubber.add_response("describe_trails", {"trailList": []})
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    result = await aws_connector.check_cloudtrail_enabled(CREDS, "us-east-1")
    assert result.status == ControlStatus.FAIL


async def test_s3_bucket_pass_when_fully_blocked(monkeypatch):
    client, stubber = _stubbed("s3")
    stubber.add_response(
        "get_public_access_block",
        {"PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True}},
        expected_params={"Bucket": "my-bucket"},
    )
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    result = await aws_connector.check_s3_bucket_not_public(CREDS, "my-bucket")
    assert result.status == ControlStatus.PASS


async def test_s3_bucket_fail_when_no_public_access_block(monkeypatch):
    client, stubber = _stubbed("s3")
    stubber.add_client_error(
        "get_public_access_block",
        service_error_code="NoSuchPublicAccessBlockConfiguration",
        service_message="The public access block configuration was not found",
        http_status_code=404,
    )
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    result = await aws_connector.check_s3_bucket_not_public(CREDS, "my-bucket")
    assert result.status == ControlStatus.FAIL


async def test_s3_bucket_needs_review_on_access_denied(monkeypatch):
    client, stubber = _stubbed("s3")
    stubber.add_client_error(
        "get_public_access_block",
        service_error_code="AccessDenied",
        service_message="Access Denied",
        http_status_code=403,
    )
    stubber.activate()
    monkeypatch.setattr(aws_connector, "_client", lambda creds, service: client)

    result = await aws_connector.check_s3_bucket_not_public(CREDS, "my-bucket")
    assert result.status == ControlStatus.NEEDS_REVIEW
