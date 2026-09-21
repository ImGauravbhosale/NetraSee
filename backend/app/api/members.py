from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, require_org_role
from app.core.db import get_db
from app.core.security import hash_password
from app.models.membership import Membership, ROLE_RANK, Role
from app.models.user import User
from app.schemas.auth import MembershipOut
from app.services.audit import write_audit_event

router = APIRouter(prefix="/api/v1/orgs/{org_id}/members", tags=["members"])


class AddMemberRequest(BaseModel):
    email: EmailStr
    name: str
    role: Role
    password: str  # v1 has no invite-email flow; the inviter sets an initial password directly


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str
    role: Role


@router.get("", response_model=list[MemberOut])
async def list_members(
    org_id: uuid.UUID, ctx: OrgContext = Depends(require_org_role(Role.VIEWER)), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Membership, User).join(User, User.id == Membership.user_id).where(Membership.organization_id == org_id)
    )
    return [
        MemberOut(user_id=user.id, email=user.email, name=user.name, role=membership.role)
        for membership, user in result.all()
    ]


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: uuid.UUID,
    payload: AddMemberRequest,
    request: Request,
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    # Only an OWNER may grant OWNER — an ADMIN escalating someone (or
    # themselves) straight to OWNER would be a privilege-escalation path.
    if ROLE_RANK[payload.role] > ROLE_RANK[ctx.role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot grant a role higher than your own")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=payload.email, name=payload.name, hashed_password=hash_password(payload.password))
        db.add(user)
        await db.flush()

    existing = await db.execute(
        select(Membership).where(Membership.user_id == user.id, Membership.organization_id == org_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member of this organization")

    membership = Membership(user_id=user.id, organization_id=org_id, role=payload.role)
    db.add(membership)

    await write_audit_event(
        db,
        organization_id=org_id,
        actor_user_id=ctx.user.id,
        action="member.added",
        resource_type="membership",
        resource_id=str(user.id),
        after_state={"email": user.email, "role": payload.role.value},
        request=request,
    )

    await db.commit()
    return MemberOut(user_id=user.id, email=user.email, name=user.name, role=payload.role)
