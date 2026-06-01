import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Date, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = {"schema": "clinical"}

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    birth_date          = Column(Date, nullable=True)
    sex                 = Column(String(10), nullable=True)
    diagnosis_category  = Column(String(100), nullable=True)
    pseudonym_id        = Column(String(50), unique=True, nullable=False)
    created_at          = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Clinician(Base):
    __tablename__ = "clinicians"
    __table_args__ = {"schema": "clinical"}

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    license_number = Column(String(100), unique=True, nullable=False)
    specialty      = Column(String(100), nullable=True)
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ClinicalRelationship(Base):
    __tablename__ = "clinical_relationships"
    __table_args__ = {"schema": "clinical"}

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinician_id = Column(UUID(as_uuid=True), ForeignKey("clinical.clinicians.id"), nullable=False, index=True)
    patient_id   = Column(UUID(as_uuid=True), ForeignKey("clinical.patients.id"), nullable=False, index=True)
    started_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at     = Column(DateTime(timezone=True), nullable=True)


class TherapyPlan(Base):
    __tablename__ = "therapy_plans"
    __table_args__ = {"schema": "clinical"}

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id   = Column(UUID(as_uuid=True), ForeignKey("clinical.patients.id"), nullable=False, index=True)
    clinician_id = Column(UUID(as_uuid=True), ForeignKey("clinical.clinicians.id"), nullable=False, index=True)
    start_date   = Column(Date, nullable=False)
    end_date     = Column(Date, nullable=True)
    status       = Column(String(20), nullable=False, default="active")
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = {"schema": "clinical"}

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name    = Column(String(200), nullable=False)
    phoneme = Column(String(20), nullable=True)
    level   = Column(Integer, nullable=False, default=1)


class ExerciseVersion(Base):
    __tablename__ = "exercise_versions"
    __table_args__ = {"schema": "clinical"}

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exercise_id         = Column(UUID(as_uuid=True), ForeignKey("clinical.exercises.id"), nullable=False, index=True)
    version             = Column(Integer, nullable=False, default=1)
    prompt_text         = Column(Text, nullable=True)
    reference_audio_key = Column(String(500), nullable=True)
    published_at        = Column(DateTime(timezone=True), nullable=True)


class Prescription(Base):
    __tablename__ = "prescriptions"
    __table_args__ = {"schema": "clinical"}

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id             = Column(UUID(as_uuid=True), ForeignKey("clinical.therapy_plans.id"), nullable=False, index=True)
    exercise_version_id = Column(UUID(as_uuid=True), ForeignKey("clinical.exercise_versions.id"), nullable=False)
    frequency_per_week  = Column(Integer, nullable=False)
    target_attempts     = Column(Integer, nullable=False)


class TherapySession(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "clinical"}

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("clinical.patients.id"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at   = Column(DateTime(timezone=True), nullable=True)


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = {"schema": "clinical"}

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id          = Column(UUID(as_uuid=True), ForeignKey("clinical.sessions.id"), nullable=False, index=True)
    exercise_version_id = Column(UUID(as_uuid=True), ForeignKey("clinical.exercise_versions.id"), nullable=False)
    audio_key           = Column(String(500), nullable=True)
    status              = Column(String(20), nullable=False, default="pending")
    submitted_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
