from fastapi import FastAPI, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session as DBSession
from typing import List
from uuid import UUID
from jose import jwt, JWTError

from app.database import get_db, engine
from app.models import (
    Base, Patient, Clinician, ClinicalRelationship,
    TherapyPlan, Exercise, ExerciseVersion, TherapySession, Attempt,
)
from app.schemas import (
    PatientCreate, PatientResponse,
    ClinicianCreate, ClinicianResponse,
    TherapyPlanCreate, TherapyPlanUpdate, TherapyPlanResponse,
    ExerciseCreate, ExerciseResponse,
    ExerciseVersionCreate, ExerciseVersionResponse,
    SessionCreate, SessionResponse,
    AttemptCreate, AttemptResponse,
)
from app.config import settings
from app.events import start_listener

Base.metadata.create_all(bind=engine)

app = FastAPI(title="clinical-service", version="1.0.0", root_path="/api/clinical")


@app.on_event("startup")
def startup_event():
    start_listener()


def get_current_user_id(authorization: str = Header(...)) -> str:
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError
        data = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return data["sub"]
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Token inválido o ausente")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "clinical-service"}


# ── Patients ──────────────────────────────────────────────────────────────────

@app.post("/patients", response_model=PatientResponse, status_code=201)
def create_patient(payload: PatientCreate, db: DBSession = Depends(get_db)):
    if db.query(Patient).filter(Patient.user_id == payload.user_id).first():
        raise HTTPException(status_code=400, detail="Paciente ya registrado")
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@app.get("/patients/me", response_model=PatientResponse)
def get_my_patient_record(
    db: DBSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Resuelve el paciente a partir del JWT: el cliente sólo conoce su user_id."""
    patient = db.query(Patient).filter(Patient.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient


@app.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: UUID, db: DBSession = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient


# ── Clinicians ────────────────────────────────────────────────────────────────

@app.post("/clinicians", response_model=ClinicianResponse, status_code=201)
def create_clinician(payload: ClinicianCreate, db: DBSession = Depends(get_db)):
    if db.query(Clinician).filter(Clinician.user_id == payload.user_id).first():
        raise HTTPException(status_code=400, detail="Clínico ya registrado")
    clinician = Clinician(**payload.model_dump())
    db.add(clinician)
    db.commit()
    db.refresh(clinician)
    return clinician


@app.get("/clinicians/me/patients", response_model=List[PatientResponse])
def get_my_patients(
    db: DBSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    clinician = db.query(Clinician).filter(Clinician.user_id == user_id).first()
    if not clinician:
        raise HTTPException(status_code=404, detail="Clínico no encontrado")

    active_rels = db.query(ClinicalRelationship).filter(
        ClinicalRelationship.clinician_id == clinician.id,
        ClinicalRelationship.ended_at.is_(None),
    ).all()

    patient_ids = [r.patient_id for r in active_rels]
    if not patient_ids:
        return []
    return db.query(Patient).filter(Patient.id.in_(patient_ids)).all()


# ── Therapy plans ─────────────────────────────────────────────────────────────

@app.get("/therapy-plans", response_model=List[TherapyPlanResponse])
def list_therapy_plans(
    patient_id: UUID = Query(..., description="Paciente cuyos planes se listan"),
    db: DBSession = Depends(get_db),
):
    return db.query(TherapyPlan).filter(
        TherapyPlan.patient_id == patient_id
    ).order_by(TherapyPlan.start_date.desc()).all()


@app.post("/therapy-plans", response_model=TherapyPlanResponse, status_code=201)
def create_therapy_plan(payload: TherapyPlanCreate, db: DBSession = Depends(get_db)):
    plan = TherapyPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@app.put("/therapy-plans/{plan_id}", response_model=TherapyPlanResponse)
def update_therapy_plan(plan_id: UUID, payload: TherapyPlanUpdate, db: DBSession = Depends(get_db)):
    plan = db.query(TherapyPlan).filter(TherapyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


# ── Exercises ─────────────────────────────────────────────────────────────────

@app.get("/exercises", response_model=List[ExerciseResponse])
def list_exercises(db: DBSession = Depends(get_db)):
    return db.query(Exercise).all()


@app.post("/exercises", response_model=ExerciseResponse, status_code=201)
def create_exercise(payload: ExerciseCreate, db: DBSession = Depends(get_db)):
    exercise = Exercise(**payload.model_dump())
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


@app.get("/exercises/{exercise_id}/versions", response_model=List[ExerciseVersionResponse])
def list_exercise_versions(exercise_id: UUID, db: DBSession = Depends(get_db)):
    if not db.query(Exercise).filter(Exercise.id == exercise_id).first():
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    return db.query(ExerciseVersion).filter(
        ExerciseVersion.exercise_id == exercise_id
    ).order_by(ExerciseVersion.version.desc()).all()


@app.post("/exercises/{exercise_id}/versions", response_model=ExerciseVersionResponse, status_code=201)
def create_exercise_version(exercise_id: UUID, payload: ExerciseVersionCreate, db: DBSession = Depends(get_db)):
    if not db.query(Exercise).filter(Exercise.id == exercise_id).first():
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    version = ExerciseVersion(exercise_id=exercise_id, **payload.model_dump())
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


# ── Sessions ──────────────────────────────────────────────────────────────────

@app.get("/sessions", response_model=List[SessionResponse])
def list_sessions(
    patient_id: UUID = Query(..., description="Paciente cuyas sesiones se listan"),
    db: DBSession = Depends(get_db),
):
    return db.query(TherapySession).filter(
        TherapySession.patient_id == patient_id
    ).order_by(TherapySession.started_at.desc()).all()


@app.get("/sessions/{session_id}/attempts", response_model=List[AttemptResponse])
def list_session_attempts(session_id: UUID, db: DBSession = Depends(get_db)):
    if not db.query(TherapySession).filter(TherapySession.id == session_id).first():
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return db.query(Attempt).filter(
        Attempt.session_id == session_id
    ).order_by(Attempt.submitted_at.desc()).all()


@app.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(payload: SessionCreate, db: DBSession = Depends(get_db)):
    if not db.query(Patient).filter(Patient.id == payload.patient_id).first():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    session = TherapySession(**payload.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# ── Attempts ──────────────────────────────────────────────────────────────────

@app.post("/attempts", response_model=AttemptResponse, status_code=201)
def create_attempt(payload: AttemptCreate, db: DBSession = Depends(get_db)):
    if not db.query(TherapySession).filter(TherapySession.id == payload.session_id).first():
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    attempt = Attempt(**payload.model_dump())
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt
