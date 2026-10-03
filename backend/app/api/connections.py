from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, require_org_role
from app.core.crypto import encrypt_secret
from app.core.db import get_db
from app.models.connection import Connection
from app.models.control import AutomationStatus, Control
from app.models.membership import Role
from app.schemas.connection import CheckResultOut, ConnectionCreateRequest, ConnectionOut, SyncResultOut
from app.services.automation import run_control_check
from app.services.audit import write_audit_event
from app.services.connectors import CONNECTORS, all_check_labels
from app.services.connectors.base import ConnectorAuthError

router = APIRouter(prefix="/api/v1/orgs/{org_id}/connections", tags=["connections"])


@router.get("", response_model=list[ConnectionOut])
async def list_connections(
    org_id: uuid.UUID, ctx: OrgContext = Depends(require_org_role(Role.VIEWER)), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Connection).where(Connection.organization_id == org_id))
    return [ConnectionOut.model_validate(c) for c in result.scalars().all()]


@router.get("/available-checks")
async def list_available_checks(
    org_id: uuid.UUID, ctx: OrgContext = Depends(require_org_role(Role.VIEWER))
):
    # Declared before the "/{connection_id}" routes below — Starlette
    # matches path patterns in declaration order, so this static segment
    # must come first or "available-checks" would be parsed as a
    # connection_id and 422 instead of matching here.
    return [{"key": key, "label": label} for key, label in all_check_labels().items()]


@router.post("", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
async def create_connection(
    org_id: uuid.UUID,
    payload: ConnectionCreateRequest,
    request: Request,
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    connector = CONNECTORS[payload.provider.value]

    # Never store a credential we haven't confirmed actually works — a
    # dead credential would otherwise sit silently until the first sync
    # fails.
    try:
        account_login = await connector.validate(payload.credentials)
    except ConnectorAuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not reach {payload.provider.value} to validate these credentials")

    connection = Connection(
        organization_id=org_id,
        provider=payload.provider,
        account_login=account_login,
        encrypted_token=encrypt_secret(json.dumps(payload.credentials)),
        created_by_user_id=ctx.user.id,
    )
    db.add(connection)
    await db.flush()

    await write_audit_event(
        db,
        organization_id=org_id,
        actor_user_id=ctx.user.id,
        action="connection.created",
        resource_type="connection",
        resource_id=str(connection.id),
        after_state={"provider": payload.provider.value, "account_login": account_login},
        request=request,
    )

    await db.commit()
    await db.refresh(connection)
    return ConnectionOut.model_validate(connection)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    org_id: uuid.UUID,
    connection_id: uuid.UUID,
    request: Request,
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    connection = await db.get(Connection, connection_id)
    if connection is None or connection.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")

    # Controls bound to this connection fall back to manual rather than
    # being left pointing at a credential that no longer exists.
    bound_result = await db.execute(
        select(Control).where(Control.automation_connection_id == connection_id)
    )
    for control in bound_result.scalars().all():
        control.automation_connection_id = None
        control.automation_check_key = None
        control.automation_target = None
        control.automation_status = AutomationStatus.MANUAL

    await write_audit_event(
        db,
        organization_id=org_id,
        actor_user_id=ctx.user.id,
        action="connection.deleted",
        resource_type="connection",
        resource_id=str(connection.id),
        before_state={"account_login": connection.account_login},
        request=request,
    )

    await db.delete(connection)
    await db.commit()


@router.post("/{connection_id}/sync", response_model=SyncResultOut)
async def sync_connection(
    org_id: uuid.UUID,
    connection_id: uuid.UUID,
    request: Request,
    ctx: OrgContext = Depends(require_org_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    connection = await db.get(Connection, connection_id)
    if connection is None or connection.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")

    bound_result = await db.execute(
        select(Control).where(Control.automation_connection_id == connection_id)
    )
    controls = bound_result.scalars().all()

    results: list[CheckResultOut] = []
    for control in controls:
        result = await run_control_check(
            db, control=control, connection=connection, actor_user_id=ctx.user.id, request=request
        )
        results.append(
            CheckResultOut(
                control_id=control.id,
                control_key=control.control_key,
                check_key=control.automation_check_key or "",
                status=result.status.value,
                summary=result.summary,
            )
        )

    connection.last_synced_at = datetime.now(timezone.utc)
    await db.commit()

    return SyncResultOut(synced_at=connection.last_synced_at, results=results)
