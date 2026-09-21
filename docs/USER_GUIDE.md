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

## 6. Roles

NetraSee has three roles in v1:

| Role | Can do |
|---|---|
| **Viewer** | Read everything — dashboard, frameworks, controls, evidence |
| **Admin** | Everything a Viewer can, plus: change control status, upload/delete evidence, add members (up to their own role), view the audit log |
| **Owner** | Everything an Admin can, plus: grant the Owner role to others |

An Admin can never grant someone Owner — only an existing Owner can do that. This
is enforced server-side, not just hidden in the UI.

## 7. Activity Log

Every status change, evidence upload/delete, and member addition writes an
append-only entry here — action, actor, resource, and (for status changes) the
before/after values. Only Owners and Admins can view it. Nothing here can be
edited or deleted after the fact.

## 8. Settings

Shows your organization name and its member list. Owners and Admins can add new
members here directly — since v1 has no invite-email flow yet, you set an initial
password for them when adding them and share it out of band.

## What's not built yet

The nav bar lists several modules — Policies, Risks, Assets, Vendors, Integrations,
Audit Center, Reports — that are visibly present but marked "soon." Clicking them
shows an honest "not built yet" page rather than fake data. See the
[Roadmap](../README.md#roadmap) in the README for what's planned.

## Troubleshooting

**"Organization not found" on an org I know exists** — you're not a member of that
org. NetraSee returns the same 404 whether the org doesn't exist or you're just not
in it, so a non-member can't even confirm the org is real.

**My upload was rejected** — check the file extension is in the allowed list above,
and the file is under 25MB.

**I can't see the Activity Log** — it's restricted to Admin and Owner roles;
Viewers don't have access.
