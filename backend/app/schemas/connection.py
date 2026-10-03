from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.connection import ConnectionProvider


class ConnectionCreateRequest(BaseModel):
    provider: ConnectionProvider = ConnectionProvider.GITHUB
    # GitHub: {"token": "ghp_..."} — AWS: {"access_key_id": "...", "secret_access_key": "...", "region": "..."}
    credentials: dict[str, str] = Field(min_length=1)


class ConnectionOut(BaseModel):
    id: uuid.UUID
    provider: ConnectionProvider
    account_login: str
    last_synced_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutomationBindRequest(BaseModel):
    connection_id: uuid.UUID
    check_key: str
    target: str = Field(min_length=1, max_length=300)


class CheckResultOut(BaseModel):
    control_id: uuid.UUID
    control_key: str
    check_key: str
    status: str
    summary: str


class SyncResultOut(BaseModel):
    synced_at: datetime
    results: list[CheckResultOut]
