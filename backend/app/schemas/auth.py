from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class MembershipOut(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    role: str


class MeResponse(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]
