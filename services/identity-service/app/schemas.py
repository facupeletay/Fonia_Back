from pydantic import BaseModel, EmailStr
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str = "patient"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str


# ── Invitation codes ──────────────────────────────────────────────────────────

class InvitationCreate(BaseModel):
    clinician_id:    UUID
    pre_filled_data: Optional[Dict[str, Any]] = None
    expiry_days:     int = 7

class InvitationResponse(BaseModel):
    id:                      UUID
    code:                    str
    created_by_clinician_id: UUID
    pre_filled_data:         Optional[Dict[str, Any]]
    expires_at:              datetime
    consumed_at:             Optional[datetime]
    consumed_by_user_id:     Optional[UUID]
    status:                  str
    created_at:              datetime
    model_config = {"from_attributes": True}

class InvitationValidateResponse(BaseModel):
    code:            str
    pre_filled_data: Optional[Dict[str, Any]]
    expires_at:      datetime

class RegisterWithCode(BaseModel):
    email:    EmailStr
    password: str
    code:     str
    role:     str = "patient"