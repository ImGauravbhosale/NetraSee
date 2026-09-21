from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.session import Session as SessionModel
from app.models.user import User
from app.schemas.auth import LoginRequest, MeResponse, MembershipOut, RegisterRequest, UserOut
from app.services.audit import write_audit_event
from app.services.rate_limit import LoginRateLimiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
rate_limiter = LoginRateLimiter()


def _set_session_cookies(response: Response, session_token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        generate_csrf_token(),
        httponly=False,  # must be readable by frontend JS to echo back as a header
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


async def _create_session(db: AsyncSession, user: User, request: Request) -> str:
    token = generate_session_token()
    session_row = SessionModel(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session_row)
    return token


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    organization = Organization(name=payload.organization_name)
    user = User(email=payload.email, name=payload.name, hashed_password=hash_password(payload.password))
    db.add_all([organization, user])
    await db.flush()  # need generated IDs before creating the membership

    membership = Membership(user_id=user.id, organization_id=organization.id, role=Role.OWNER)
    db.add(membership)

    await write_audit_event(
        db,
        organization_id=organization.id,
        actor_user_id=user.id,
        action="user.registered",
        resource_type="user",
        resource_id=str(user.id),
        after_state={"email": user.email},
        request=request,
    )

    token = await _create_session(db, user, request)
    await db.commit()

    _set_session_cookies(response, token)
    return {"user_id": str(user.id), "organization_id": str(organization.id)}


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"{client_ip}:{payload.email}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts — try again later")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = await _create_session(db, user, request)
    await db.commit()

    _set_session_cookies(response, token)
    return {"user_id": str(user.id)}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        token_hash = hash_session_token(token)
        result = await db.execute(select(SessionModel).where(SessionModel.token_hash == token_hash))
        session_row = result.scalar_one_or_none()
        if session_row is not None:
            await db.delete(session_row)
            await db.commit()

    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == current_user.id)
    )
    memberships = [
        MembershipOut(organization_id=m.organization_id, organization_name=org.name, role=m.role.value)
        for m, org in result.all()
    ]
    return MeResponse(user=UserOut.model_validate(current_user), memberships=memberships)
