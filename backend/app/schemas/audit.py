from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str
    before_state: dict | None
    after_state: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
