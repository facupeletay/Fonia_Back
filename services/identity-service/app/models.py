from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone
import uuid
from app.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(50), nullable=False, default="patient")
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "identity"}

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class InvitationCode(Base):
    __tablename__ = "invitation_codes"
    __table_args__ = {"schema": "identity"}

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code                    = Column(String(12), unique=True, nullable=False, index=True)
    created_by_clinician_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pre_filled_data         = Column(JSONB, nullable=True)
    expires_at              = Column(DateTime(timezone=True), nullable=False)
    consumed_at             = Column(DateTime(timezone=True), nullable=True)
    consumed_by_user_id     = Column(UUID(as_uuid=True), nullable=True)
    status                  = Column(String(20), nullable=False, default="active")
    created_at              = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))