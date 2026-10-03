# NetraSee User Guide

This walks through using NetraSee as an end user — from creating your organization
to understanding why a control is failing and fixing it. It assumes the app is
already running (see the [Quick start](../README.md#quick-start) in the README).

## 1. Create your organization

Go to `/register`. The first person to register an org becomes its **Owner** —
there's no separate admin setup step. You'll need:

- Organization name
- Your name and email
- A password (10+ characters)

If you just want to explore without creating anything, use the seeded demo account
instead: `demo@example.com` / `netrasee-demo-1234`.

## 2. The Dashboard

After logging in you land on **Compliance Posture** — this is the honest state of
your org right now, not a snapshot from your last audit:

- One card per adopted framework, with a live progress percentage
- Control counts by status (Passing / Failing / Needs review / Not applicable / Not
  tested)
- Evidence counts by status (Valid / Expiring soon / Expired / Under review)

Every number here is computed at request time from your actual controls and
evidence — change a control's status or let a piece of evidence expire, and the
dashboard reflects it on the next load.

## 3. Frameworks

**Frameworks** page lists everything your org has adopted. Click into one to see its
requirement tree — each requirement shows how many of its mapped controls are
currently passing (e.g. `1/2`).

A framework's progress percentage is: passing controls ÷ total controls mapped to
its requirements. A single control can satisfy requirements in *multiple*
frameworks at once — that's deliberate. In the seed data, one "MFA enforced"
control is mapped to both SOC 2's CC6 and ISO 27001's A.8, so fixing it moves both
frameworks forward together instead of duplicating the work.

NetraSee's global catalog ships with six frameworks: SOC 2, ISO 27001, GDPR,
PCI DSS v4.0, HIPAA Security Rule, and NIST CSF 2.0 — each seeded from that
framework's own published structure (see the table in the
[README](../README.md#framework-catalog)). Any not yet adopted show up under
**Adopt a framework** at the bottom of the page (Owner/Admin only) — adopting one
just makes its requirements available to map controls against; it doesn't create
any controls for you.

## 4. Controls

**Controls** lists every control in your org, with a status filter dropdown. Each
row shows:

- Control key + name (e.g. `CTRL-002 — Centralized audit logging is enabled...`)
- Category
- Automation level (Manual / Automated / Hybrid)
- Status

Click a control to drill in. This is the page the whole app is built around: if a
control is **failing**, the page tells you why —

- No evidence is attached, or
- All attached evidence has expired, or
- Evidence exists but hasn't been reviewed and marked passing yet

From there you see the exact evidence items and their status, the frameworks/
requirements this control satisfies, and — if you're an Owner or Admin — a status
dropdown to update it directly. Every status change is recorded in the Activity
Log with who changed it and when.

## 5. Evidence

**Evidence** is where you upload the actual documents that prove a control works —
screenshots, exported configs, signed attestations, log exports. Allowed file
types: `pdf`, `png`, `jpg`, `jpeg`, `txt`, `json`, `csv`, `zip` (25MB cap).

When uploading (Owner/Admin only), you can:

- Set an expiry date — evidence doesn't stay valid forever, and NetraSee will
  automatically flag it as **Expiring soon** within 14 days of expiry, then
  **Expired** once it passes
- Link it to one or more controls directly, so it shows up on those controls'
  detail pages immediately

Deleting evidence is permanent and removes the underlying file — it also writes an
audit event so there's a record of who deleted what and when.

### Evidence statuses

| Status | Meaning |
|---|---|
| `VALID` | Has an expiry date in the future, more than 14 days out (or no expiry at all) |
| `EXPIRING` | Expires within the next 14 days |
| `EXPIRED` | Expiry date has passed |
| `UNDER_REVIEW` | Manually flagged as under review — takes priority over the date-based statuses |

## 6. Integrations — automated controls

**Integrations** is where you connect a real account so NetraSee can evaluate
controls itself instead of waiting on a human to upload evidence. Two providers
are supported:

1. Click **Connect GitHub** and paste a personal access token with `repo` and
   `read:org` scopes, **or** click **Connect AWS** and enter an access key ID +
   secret access key (read-only IAM credentials recommended) and a region.
   NetraSee validates the credentials against the real API before saving
   anything — dead or mistyped credentials are rejected immediately, not
   discovered on the first sync. Credentials are encrypted at rest and never
   shown again, including to you.
2. Open a control's detail page and use the **Automation** panel to bind it to
   one of the available checks and a target:
   - GitHub: branch protection, org-wide 2FA, Dependabot alerts, secret
     scanning — target is `owner/repo`, or just the org login for 2FA.
   - AWS: root account MFA, all IAM users have MFA, CloudTrail logging, S3
     bucket public-access block — target is a bucket name or region for the
     resource-scoped checks (the account-wide checks ignore it; put anything,
     e.g. `account`).
3. Back on **Integrations**, click **Sync now** on that connection. NetraSee
   calls the provider live, computes PASS/FAIL/NEEDS_REVIEW for every control
   bound to it, and shows you the exact result for each.

Once a control is bound to automation:

- Its status can no longer be changed with the manual status dropdown — the
  PATCH is rejected server-side, not just hidden in the UI, so a real failure
  can't be quietly clicked away to PASS.
- Every sync creates a real Evidence entry containing the provider's exact API
  response, visible from the control's detail page alongside its summary (e.g.
  *"Branch 'main' on acme/widgets has no protection rules configured"* or
  *"MFA is NOT enabled on the AWS root account"*) — not just a status, but what
  produced it.
- This automated evidence expires after 24 hours, so a control can't keep
  reading as compliant indefinitely off a single stale sync.

Unbind a control from its **Automation** panel at any time to make it manual
again. Disconnecting a connection entirely automatically unbinds every control
that depended on it, rather than leaving them pointed at a dead credential.

A check that can't attribute its result to the control itself — a missing
permission, a resource the credentials can't see, a network error — comes back
as **NEEDS_REVIEW**, never a false FAIL or false PASS.

## 7. Roles

NetraSee has three roles in v1:

| Role | Can do |
|---|---|
| **Viewer** | Read everything — dashboard, frameworks, controls, evidence |
| **Admin** | Everything a Viewer can, plus: change control status, upload/delete evidence, connect integrations and bind automation, add members (up to their own role), view the audit log |
| **Owner** | Everything an Admin can, plus: grant the Owner role to others |

An Admin can never grant someone Owner — only an existing Owner can do that. This
is enforced server-side, not just hidden in the UI.

## 8. Activity Log

Every status change, evidence upload/delete, member addition, connection, and
automated check writes an append-only entry here — action, actor, resource, and
(for status changes) the before/after values. Only Owners and Admins can view it.
Nothing here can be edited or deleted after the fact.

## 9. Settings

Shows your organization name and its member list. Owners and Admins can add new
members here directly — since v1 has no invite-email flow yet, you set an initial
password for them when adding them and share it out of band.

## What's not built yet

The nav bar lists several modules — Policies, Risks, Assets, Vendors, Audit
Center, Reports — that are visibly present but marked "soon." Clicking them
shows an honest "not built yet" page rather than fake data. See the
[Roadmap](../README.md#roadmap) in the README for what's planned.

## Troubleshooting

**"Organization not found" on an org I know exists** — you're not a member of that
org. NetraSee returns the same 404 whether the org doesn't exist or you're just not
in it, so a non-member can't even confirm the org is real.

**My upload was rejected** — check the file extension is in the allowed list above,
and the file is under 25MB.

**My GitHub connection won't save** — the token is rejected if GitHub itself
rejects it (expired, revoked, or wrong scopes). Confirm it has `repo` and
`read:org` scopes and hasn't expired.

**My AWS connection won't save** — the access key pair is rejected if AWS
itself rejects it. Confirm the key is active (not deleted/deactivated in IAM)
and that you copied both the access key ID and secret access key correctly —
AWS only shows the secret once, at creation.

**A bound control keeps coming back NEEDS_REVIEW** — this means the check ran
but couldn't attribute a real pass/fail to your credentials' access: usually
they can't see the resource, or lack the permission that specific check needs
(e.g. GitHub's branch protection and secret scanning both need repo admin
access; AWS's checks need the relevant `iam:`, `cloudtrail:`, or `s3:` read
permissions).

**I can't see the Activity Log** — it's restricted to Admin and Owner roles;
Viewers don't have access.
