"""Unit tests for the GitHub connector against mocked HTTP responses
shaped exactly like the real API (status codes and body shapes taken
from GitHub's published REST documentation) — verifying NetraSee's own
PASS/FAIL/NEEDS_REVIEW mapping logic, not GitHub's API itself."""
import httpx
import pytest
import respx

from app.core.config import settings
from app.models.control import ControlStatus
from app.services.connectors import github

BASE = settings.github_api_base_url
CREDS = {"token": "tok"}


@pytest.mark.respx(base_url=BASE)
async def test_validate_returns_login(respx_mock):
    respx_mock.get("/user").mock(return_value=httpx.Response(200, json={"login": "octocat"}))
    login = await github.validate(CREDS)
    assert login == "octocat"


@pytest.mark.respx(base_url=BASE)
async def test_validate_rejects_bad_token(respx_mock):
    respx_mock.get("/user").mock(return_value=httpx.Response(401, json={"message": "Bad credentials"}))
    with pytest.raises(github.GithubAuthError):
        await github.validate({"token": "bad-tok"})


@pytest.mark.respx(base_url=BASE)
async def test_branch_protection_pass_when_reviews_required(respx_mock):
    respx_mock.get("/repos/acme/widgets").mock(
        return_value=httpx.Response(200, json={"default_branch": "main"})
    )
    respx_mock.get("/repos/acme/widgets/branches/main/protection").mock(
        return_value=httpx.Response(200, json={"required_pull_request_reviews": {"required_approving_review_count": 1}})
    )
    result = await github.check_branch_protection(CREDS, "acme/widgets")
    assert result.status == ControlStatus.PASS


@pytest.mark.respx(base_url=BASE)
async def test_branch_protection_fail_when_unprotected(respx_mock):
    respx_mock.get("/repos/acme/widgets").mock(
        return_value=httpx.Response(200, json={"default_branch": "main"})
    )
    respx_mock.get("/repos/acme/widgets/branches/main/protection").mock(return_value=httpx.Response(404))
    result = await github.check_branch_protection(CREDS, "acme/widgets")
    assert result.status == ControlStatus.FAIL


@pytest.mark.respx(base_url=BASE)
async def test_branch_protection_needs_review_on_missing_repo(respx_mock):
    respx_mock.get("/repos/acme/ghost").mock(return_value=httpx.Response(404))
    result = await github.check_branch_protection(CREDS, "acme/ghost")
    assert result.status == ControlStatus.NEEDS_REVIEW


@pytest.mark.respx(base_url=BASE)
async def test_org_2fa_pass_when_enforced(respx_mock):
    respx_mock.get("/orgs/acme").mock(return_value=httpx.Response(200, json={"two_factor_requirement_enabled": True}))
    result = await github.check_org_2fa_enforced(CREDS, "acme")
    assert result.status == ControlStatus.PASS


@pytest.mark.respx(base_url=BASE)
async def test_org_2fa_fail_when_not_enforced(respx_mock):
    respx_mock.get("/orgs/acme").mock(return_value=httpx.Response(200, json={"two_factor_requirement_enabled": False}))
    result = await github.check_org_2fa_enforced(CREDS, "acme")
    assert result.status == ControlStatus.FAIL


@pytest.mark.respx(base_url=BASE)
async def test_dependabot_alerts_pass_on_204(respx_mock):
    respx_mock.get("/repos/acme/widgets/vulnerability-alerts").mock(return_value=httpx.Response(204))
    result = await github.check_dependabot_alerts(CREDS, "acme/widgets")
    assert result.status == ControlStatus.PASS


@pytest.mark.respx(base_url=BASE)
async def test_dependabot_alerts_fail_on_404(respx_mock):
    respx_mock.get("/repos/acme/widgets/vulnerability-alerts").mock(return_value=httpx.Response(404))
    result = await github.check_dependabot_alerts(CREDS, "acme/widgets")
    assert result.status == ControlStatus.FAIL


@pytest.mark.respx(base_url=BASE)
async def test_secret_scanning_pass_when_enabled(respx_mock):
    respx_mock.get("/repos/acme/widgets").mock(
        return_value=httpx.Response(
            200, json={"security_and_analysis": {"secret_scanning": {"status": "enabled"}}}
        )
    )
    result = await github.check_secret_scanning(CREDS, "acme/widgets")
    assert result.status == ControlStatus.PASS


@pytest.mark.respx(base_url=BASE)
async def test_secret_scanning_needs_review_when_unreported(respx_mock):
    respx_mock.get("/repos/acme/widgets").mock(return_value=httpx.Response(200, json={}))
    result = await github.check_secret_scanning(CREDS, "acme/widgets")
    assert result.status == ControlStatus.NEEDS_REVIEW
