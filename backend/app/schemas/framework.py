from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class RequirementOut(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    description: str
    control_count: int
    passing_count: int

    model_config = ConfigDict(from_attributes=True)


class FrameworkOut(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class AdoptedFrameworkOut(BaseModel):
    framework: FrameworkOut
    adopted_at: str
    progress_percent: float
    requirements: list[RequirementOut]
