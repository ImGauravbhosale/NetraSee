from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.evidence import EvidenceStatus


class EvidenceControlRef(BaseModel):
    control_id: uuid.UUID
    control_key: str
    control_name: str


class EvidenceOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    source: str
    collected_at: datetime
    expires_at: datetime | None
    status: EvidenceStatus
    checksum_sha256: str
    collection_method: str
    owner_user_id: uuid.UUID | None
    controls: list[EvidenceControlRef]

    model_config = ConfigDict(from_attributes=True)
