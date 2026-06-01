import json
import logging
import threading
import time
import uuid

import redis

from app.config import settings
from app.database import SessionLocal
from app.models import Patient, Clinician, ClinicalRelationship

logger = logging.getLogger(__name__)

CHANNEL = "identity.events"


def _handle_patient_registered(data: dict) -> None:
    user_id      = data.get("user_id")
    clinician_id = data.get("clinician_id")
    pre_filled   = data.get("pre_filled_data") or {}

    db = SessionLocal()
    try:
        if db.query(Patient).filter(Patient.user_id == user_id).first():
            logger.info("Paciente %s ya existe, evento ignorado", user_id)
            return

        patient = Patient(
            user_id            = user_id,
            diagnosis_category = pre_filled.get("diagnóstico") or pre_filled.get("diagnosis"),
            pseudonym_id       = str(uuid.uuid4()),
        )
        db.add(patient)
        db.flush()

        clinician = db.query(Clinician).filter(Clinician.user_id == clinician_id).first()
        if not clinician:
            db.rollback()
            logger.error("Clinician con user_id %s no encontrado, no se crea la relación", clinician_id)
            return

        rel = ClinicalRelationship(
            clinician_id = clinician.id,
            patient_id   = patient.id,
        )
        db.add(rel)
        db.commit()
        logger.info("Paciente %s y relación con clínico %s creados desde evento", user_id, clinician_id)
    except Exception as e:
        db.rollback()
        logger.error("Error procesando PatientRegisteredWithInvitation: %s", e)
    finally:
        db.close()


def _listen() -> None:
    while True:
        try:
            r = redis.from_url(settings.redis_url, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe(CHANNEL)
            logger.info("Suscripto al canal Redis: %s", CHANNEL)
            for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    if data.get("event") == "PatientRegisteredWithInvitation":
                        _handle_patient_registered(data)
                except Exception as e:
                    logger.error("Error parseando evento: %s", e)
        except Exception as e:
            logger.error("Conexión Redis perdida: %s — reintentando en 5s", e)
            time.sleep(5)


def start_listener() -> None:
    thread = threading.Thread(target=_listen, daemon=True)
    thread.start()
    logger.info("Event listener iniciado")
