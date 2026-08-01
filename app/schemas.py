from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
class UserBase(BaseModel):
    email: str
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()
class UserCreate(UserBase):
    password: str
class UserResponse(BaseModel):
    id: int
    email: str
    is_verified: bool
    created_at: datetime
    class Config:
        from_attributes = True
class DeviceBase(BaseModel):
    name: str
    peer_id: str
    mac_address: Optional[str] = None
    notes: Optional[str] = None
class DeviceCreate(DeviceBase):
    pass
class DeviceResponse(DeviceBase):
    id: int
    user_id: int
    is_online: bool
    last_seen: datetime
    class Config:
        from_attributes = True
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
class VerifyEmail(BaseModel):
    email: str
    code: str
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()
