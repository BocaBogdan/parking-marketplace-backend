import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from parking_marketplace_backend.models.user import UserRole

E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    apartment_number: str = Field(min_length=1, max_length=50)
    phone: str
    email: EmailStr
    # bcrypt only considers the first 72 bytes of a password
    password: str = Field(min_length=8, max_length=72)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not E164_PATTERN.match(value):
            raise ValueError("phone must be in E.164 format, e.g. +14155552671")
        return value


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    apartment_number: str
    phone: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    updated_at: datetime
