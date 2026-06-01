from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from enum import Enum


class SexEnum(str, Enum):
    male   = "male"
    female = "female"
    other  = "other"


class PlanStatus(str, Enum):
    active    = "active"
    paused    = "paused"
    completed = "completed"
    cancelled = "cancelled"


class AttemptStatus(str, Enum):
    pending  = "pending"
    reviewed = "reviewed"


# ── Patient ──────────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    user_id:            UUID
    birth_date:         date
    sex:                SexEnum
    diagnosis_category: Optional[str] = None
    pseudonym_id:       str

class PatientResponse(BaseModel):
    id:                 UUID
    user_id:            UUID
    birth_date:         date
    sex:                SexEnum
    diagnosis_category: Optional[str]
    pseudonym_id:       str
    created_at:         datetime
    model_config = {"from_attributes": True}


# ── Clinician ─────────────────────────────────────────────────────────────────

class ClinicianCreate(BaseModel):
    user_id:        UUID
    license_number: str
    specialty:      Optional[str] = None

class ClinicianResponse(BaseModel):
    id:             UUID
    user_id:        UUID
    license_number: str
    specialty:      Optional[str]
    created_at:     datetime
    model_config = {"from_attributes": True}


# ── TherapyPlan ───────────────────────────────────────────────────────────────

class TherapyPlanCreate(BaseModel):
    patient_id:   UUID
    clinician_id: UUID
    start_date:   date
    end_date:     Optional[date] = None
    status:       PlanStatus = PlanStatus.active

class TherapyPlanUpdate(BaseModel):
    end_date: Optional[date]      = None
    status:   Optional[PlanStatus] = None

class TherapyPlanResponse(BaseModel):
    id:           UUID
    patient_id:   UUID
    clinician_id: UUID
    start_date:   date
    end_date:     Optional[date]
    status:       PlanStatus
    created_at:   datetime
    model_config = {"from_attributes": True}


# ── Exercise ──────────────────────────────────────────────────────────────────

class ExerciseCreate(BaseModel):
    name:    str
    phoneme: Optional[str] = None
    level:   int = 1

class ExerciseResponse(BaseModel):
    id:      UUID
    name:    str
    phoneme: Optional[str]
    level:   int
    model_config = {"from_attributes": True}


# ── ExerciseVersion ───────────────────────────────────────────────────────────

class ExerciseVersionCreate(BaseModel):
    version:             int = 1
    prompt_text:         Optional[str] = None
    reference_audio_key: Optional[str] = None
    published_at:        Optional[datetime] = None

class ExerciseVersionResponse(BaseModel):
    id:                  UUID
    exercise_id:         UUID
    version:             int
    prompt_text:         Optional[str]
    reference_audio_key: Optional[str]
    published_at:        Optional[datetime]
    model_config = {"from_attributes": True}


# ── Session ───────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    patient_id: UUID
    started_at: Optional[datetime] = None
    ended_at:   Optional[datetime] = None

class SessionResponse(BaseModel):
    id:         UUID
    patient_id: UUID
    started_at: datetime
    ended_at:   Optional[datetime]
    model_config = {"from_attributes": True}


# ── Attempt ───────────────────────────────────────────────────────────────────

class AttemptCreate(BaseModel):
    session_id:          UUID
    exercise_version_id: UUID
    audio_key:           Optional[str] = None
    status:              AttemptStatus = AttemptStatus.pending
    submitted_at:        Optional[datetime] = None

class AttemptResponse(BaseModel):
    id:                  UUID
    session_id:          UUID
    exercise_version_id: UUID
    audio_key:           Optional[str]
    status:              AttemptStatus
    submitted_at:        datetime
    model_config = {"from_attributes": True}
