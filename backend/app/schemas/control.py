from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.control import AutomationStatus, ControlStatus


class RequirementMappingOut(BaseModel):
    requirement_id: uuid.UUID
    requirement_key: str
    requirement_name: str
    framework_key: str
    framework_name: str


class ControlEvidenceOut(BaseModel):
    id: uuid.UUID
    name: str
    status: str


class ControlListItemOut(BaseModel):
    id: uuid.UUID
    control_key: str
    name: str
    category: str
    status: ControlStatus
    automation_status: AutomationStatus
    owner_user_id: uuid.UUID | None
    next_review_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ControlDetailOut(ControlListItemOut):
    description: str
    objective: str
    testing_frequency: str
    last_tested_at: datetime | None
    requirements: list[RequirementMappingOut]
    evidence: list[ControlEvidenceOut]


class ControlUpdateRequest(BaseModel):
    status: ControlStatus | None = None
    owner_user_id: uuid.UUID | None = None
    next_review_at: datetime | None = None


class ControlCreateRequest(BaseModel):
    control_key: str
    name: str
    description: str = ""
    objective: str = ""
    category: str = ""
    automation_status: AutomationStatus = AutomationStatus.MANUAL
    testing_frequency: str = "quarterly"
    requirement_ids: list[uuid.UUID] = []
