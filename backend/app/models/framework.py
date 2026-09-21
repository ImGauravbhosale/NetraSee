from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Framework(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The global catalog — SOC 2, ISO 27001, etc. Not org-owned: every
    organization sees the same framework/requirement definitions and
    adopts a subset via OrganizationFramework."""

    __tablename__ = "frameworks"

    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # "soc2", "iso27001"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class Requirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A structural section of a framework — SOC 2's CC6, ISO 27001's A.8.
    Controls map to these, not directly to the framework, so one control
    can satisfy a specific requirement across multiple frameworks."""

    __tablename__ = "requirements"
    __table_args__ = (UniqueConstraint("framework_id", "key", name="uq_requirement_framework_key"),)

    framework_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(50), nullable=False)  # "CC6", "A.8"
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class OrganizationFramework(Base, UUIDPrimaryKeyMixin):
    """Which frameworks an organization has adopted."""

    __tablename__ = "organization_frameworks"
    __table_args__ = (UniqueConstraint("organization_id", "framework_id", name="uq_org_framework"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    framework_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    adopted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
