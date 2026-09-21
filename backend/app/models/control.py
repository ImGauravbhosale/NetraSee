from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ControlStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_TESTED = "NOT_TESTED"


class AutomationStatus(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTOMATED = "AUTOMATED"
    HYBRID = "HYBRID"


class Control(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An org's own instance of a control — even when seeded from a
    template, each organization owns and customizes its controls. This is
    what lets one control satisfy multiple frameworks: it links to many
    Requirements via ControlRequirementLink instead of belonging to one."""

    __tablename__ = "controls"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    control_key: Mapped[str] = mapped_column(String(50), nullable=False)  # org-local, e.g. "CTRL-014"
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[ControlStatus] = mapped_column(
        Enum(ControlStatus, name="control_status"), nullable=False, default=ControlStatus.NOT_TESTED
    )
    automation_status: Mapped[AutomationStatus] = mapped_column(
        Enum(AutomationStatus, name="control_automation_status"),
        nullable=False,
        default=AutomationStatus.MANUAL,
    )
    testing_frequency: Mapped[str] = mapped_column(String(50), nullable=False, default="quarterly")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ControlRequirementLink(Base, UUIDPrimaryKeyMixin):
    """The reusability mechanism: one Control can satisfy many
    Requirements across different frameworks, and one Requirement can be
    satisfied by many Controls."""

    __tablename__ = "control_requirement_links"
    __table_args__ = (
        UniqueConstraint("control_id", "requirement_id", name="uq_control_requirement"),
    )

    control_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("controls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
