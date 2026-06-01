from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import uuid
import random
import string

from app.database import get_db, engine
from app.models import Base, User, RefreshToken, InvitationCode
from app.schemas import (
    UserRegister, UserLogin, UserResponse, TokenResponse, RefreshRequest,
    InvitationCreate, InvitationResponse, InvitationValidateResponse, RegisterWithCode,
)
from app.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.config import settings


def _generate_code(db: Session) -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "PFI-" + "".join(random.choices(chars, k=8))
        if not db.query(InvitationCode).filter(InvitationCode.code == code).first():
            return code


def _get_active_invitation(code: str, db: Session) -> InvitationCode:
    inv = db.query(InvitationCode).filter(InvitationCode.code == code).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Código no encontrado")
    if inv.status != "active":
        raise HTTPException(status_code=400, detail=f"Código {inv.status}")
    if inv.expires_at < datetime.now(timezone.utc):
        inv.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Código expirado")
    return inv

Base.metadata.create_all(bind=engine)

app = FastAPI(title="identity-service", version="1.0.0", root_path="/api/identity")

@app.get("/health")
def health():
    return {"status": "ok", "service": "identity-service"}

@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access  = create_access_token({"sub": str(user.id), "role": user.role})
    refresh = create_refresh_token({"sub": str(user.id)})

    token = RefreshToken(
        user_id=user.id,
        token_hash=sha256(refresh.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(token)
    db.commit()

    return TokenResponse(access_token=access, refresh_token=refresh)

@app.post("/auth/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    token_hash = sha256(payload.refresh_token.encode()).hexdigest()
    stored = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False
    ).first()
    if not stored:
        raise HTTPException(status_code=401, detail="Token revocado o no encontrado")

    stored.revoked = True
    db.commit()

    user = db.query(User).filter(User.id == data["sub"]).first()
    access  = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    new_token = RefreshToken(
        user_id=user.id,
        token_hash=sha256(new_refresh.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_token)
    db.commit()

    return TokenResponse(access_token=access, refresh_token=new_refresh)

@app.post("/auth/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = sha256(payload.refresh_token.encode()).hexdigest()
    stored = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()
    if stored:
        stored.revoked = True
        db.commit()
    return {"status": "ok"}


@app.post("/auth/register-with-code", response_model=UserResponse, status_code=201)
def register_with_code(payload: RegisterWithCode, db: Session = Depends(get_db)):
    inv = _get_active_invitation(payload.code, db)
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()  # obtiene user.id antes del commit
    inv.status              = "consumed"
    inv.consumed_at         = datetime.now(timezone.utc)
    inv.consumed_by_user_id = user.id
    db.commit()
    db.refresh(user)
    return user


# ── Invitations ───────────────────────────────────────────────────────────────

@app.post("/invitations", response_model=InvitationResponse, status_code=201)
def create_invitation(payload: InvitationCreate, db: Session = Depends(get_db)):
    inv = InvitationCode(
        code                    = _generate_code(db),
        created_by_clinician_id = payload.clinician_id,
        pre_filled_data         = payload.pre_filled_data,
        expires_at              = datetime.now(timezone.utc) + timedelta(days=payload.expiry_days),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@app.get("/invitations/clinician/{clinician_id}", response_model=list[InvitationResponse])
def list_clinician_invitations(clinician_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(InvitationCode).filter(
        InvitationCode.created_by_clinician_id == clinician_id
    ).order_by(InvitationCode.created_at.desc()).all()


@app.post("/invitations/{code}/validate", response_model=InvitationValidateResponse)
def validate_invitation(code: str, db: Session = Depends(get_db)):
    inv = _get_active_invitation(code, db)
    return InvitationValidateResponse(
        code            = inv.code,
        pre_filled_data = inv.pre_filled_data,
        expires_at      = inv.expires_at,
    )


@app.delete("/invitations/{code}", status_code=200)
def revoke_invitation(code: str, db: Session = Depends(get_db)):
    inv = db.query(InvitationCode).filter(InvitationCode.code == code).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Código no encontrado")
    if inv.status in ("consumed", "revoked"):
        raise HTTPException(status_code=400, detail=f"No se puede revocar un código {inv.status}")
    inv.status = "revoked"
    db.commit()
    return {"status": "revoked", "code": inv.code}