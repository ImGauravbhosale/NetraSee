# Security Policy

NetraSee is a compliance platform — we hold ourselves to the same bar we check
for in other people's GitHub orgs and AWS accounts. If you find a real
vulnerability here, we want to know before anyone else does.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Use [GitHub's private vulnerability reporting](https://github.com/ImGauravbhosale/NetraSee/security/advisories/new)
on this repository instead. It creates a private draft advisory visible only to
the maintainer and you, so the issue isn't public until there's a fix.

Include:
- What you found and where (file/endpoint/flow)
- Steps to reproduce
- What you think the impact is (what a real attacker could actually do with it)

## What's in scope

- The backend API (`backend/app`) — auth, tenant isolation, evidence handling,
  connector credential storage, any endpoint
- The frontend (`frontend/app`) — XSS, CSRF, auth bypass in the UI layer
- The connector modules (`backend/app/services/connectors`) — anything that
  could leak a connected GitHub token or AWS credential, or misreport a
  control's real status

## What's out of scope

- Findings that require physical access to a user's machine
- Social engineering
- Denial of service against the demo/local dev environment
- Issues already listed in the [README's Roadmap](README.md#roadmap) as
  explicitly deferred (e.g. no SSO/MFA on NetraSee's own login yet) — these
  are known gaps, not undisclosed vulnerabilities

## Response

This is an open-source project maintained outside of full-time work, not a
company with an SLA. Expect an initial response within a few days, not hours.
Credit is given in the advisory and release notes unless you ask not to be
named.
