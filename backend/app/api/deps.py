"""Every org-scoped dependency in this file resolves membership from the
database first — never from a role/org_id trusted off the request itself
(a header, a body field, a query param). This is the one piece of logic
the whole tenant-isolation guarantee rests on.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import csrf_tokens_match, hash_session_token
from app.models.membership import ROLE_RANK, Membership, Role
from app.models.session import Session as SessionModel
from app.models.user import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    token_hash = hash_session_token(token)
    result = await db.execute(select(SessionModel).where(SessionModel.token_hash == token_hash))
    session_row = result.scalar_one_or_none()
    if session_row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if session_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    user = await db.get(User, session_row.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


def require_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    netrasee_csrf: str | None = Cookie(default=None, alias="netrasee_csrf"),
) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if not csrf_tokens_match(netrasee_csrf, x_csrf_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF token missing or invalid")


class OrgContext:
    def __init__(self, organization_id: uuid.UUID, user: User, role: Role):
        self.organization_id = organization_id
        self.user = user
        self.role = role


def require_org_role(min_role: Role = Role.VIEWER):
    """Returns a FastAPI dependency that resolves the caller's membership
    in the org named by the `org_id` path parameter, and rejects the
    request outright if no membership exists — this is what makes
    cross-tenant access fail closed rather than needing every route to
    remember to check."""

    async def _dependency(
        org_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> OrgContext:
        result = await db.execute(
            select(Membership).where(
                Membership.user_id == current_user.id,
                Membership.organization_id == org_id,
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None:
            # 404, not 403 — don't confirm the org exists to a non-member.
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
        if ROLE_RANK[membership.role] < ROLE_RANK[min_role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role for this action")
        return OrgContext(organization_id=org_id, user=current_user, role=membership.role)

    return _dependency
