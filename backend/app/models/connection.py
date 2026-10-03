from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConnectionProvider(str, enum.Enum):
    GITHUB = "GITHUB"
    AWS = "AWS"


class Connection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A credential NetraSee uses to automatically evaluate controls
    against a real external account. The token is stored encrypted
    (app.core.crypto) — never in plaintext — and is never returned by any
    API response, only used server-side to make the provider API call."""

    __tablename__ = "connections"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[ConnectionProvider] = mapped_column(
        Enum(ConnectionProvider, name="connection_provider"), nullable=False
    )
    account_login: Mapped[str] = mapped_column(String(300), nullable=False)
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
