import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)

class UserRead(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID
    username: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime