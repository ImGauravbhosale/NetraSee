from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Role(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    VIEWER = "VIEWER"


# Ordered weakest-to-strongest so a single ">=" comparison expresses
# "at least this role" without scattering role-list checks everywhere.
ROLE_RANK: dict[Role, int] = {Role.VIEWER: 0, Role.ADMIN: 1, Role.OWNER: 2}


class Membership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A user's role within one organization. This is *the* tenant
    boundary — every org-scoped query starts from "does a Membership
    linking this user to this org_id exist," not from trusting an ID in
    the URL."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[Role] = mapped_column(Enum(Role, name="membership_role"), nullable=False)
