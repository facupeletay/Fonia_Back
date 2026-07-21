# Diagrama de Clases (UML) — Plataforma PFI

> Diagrama de clases UML que representa el modelo de dominio del backend, derivado de
> los modelos ORM SQLAlchemy (`models.py`) y los esquemas Pydantic (`schemas.py`) de
> cada microservicio.
>
> Sintaxis: **Mermaid** (`classDiagram`). Se muestran atributos, tipos y relaciones.
> Se omiten getters/setters por tratarse de entidades de datos (POPO/ORM).
>
> 🟢 = real / implementado · 🟡 = planificado (objetivo v2.1, ver
> [`Arquitectura-Logica.md`](Arquitectura-Logica.md)). Las secciones 3–6 documentan el
> modelo de dominio **objetivo** de los servicios en estado esqueleto.

---

## 1. Módulo de Identidad (`identity-service`) 🟢

> 🖼️ Imagen renderizada: [`img/03-clases-identity.png`](img/03-clases-identity.png) · vectorial: [`img/03-clases-identity.svg`](img/03-clases-identity.svg)

![Diagrama de clases identity-service](img/03-clases-identity.png)

```mermaid
classDiagram
    class User {
        +UUID id
        +str email  «unique»
        +str password_hash
        +str role = "patient"
        +bool is_active = true
        +datetime created_at
    }

    class RefreshToken {
        +UUID id
        +UUID user_id
        +str token_hash  «SHA-256»
        +datetime expires_at
        +bool revoked = false
        +datetime created_at
    }

    class InvitationCode {
        +UUID id
        +str code  «PFI-XXXXXXXX, unique»
        +UUID created_by_clinician_id
        +JSONB pre_filled_data
        +datetime expires_at
        +datetime consumed_at
        +UUID consumed_by_user_id
        +str status = "active"
        +datetime created_at
    }

    User "1" --> "0..*" RefreshToken : posee
    User "1" --> "0..*" InvitationCode : consume
    InvitationCode ..> User : created_by_clinician (lógico)
```

**Notas de diseño:**
- `RefreshToken.user_id` e `InvitationCode.consumed_by_user_id` referencian a `User`
  por UUID pero **sin FK física** (desacoplamiento; la integridad es lógica).
- `status` de `InvitationCode` es una máquina de estados: `active → consumed | revoked | expired`.

---

## 2. Módulo Clínico (`clinical-service`) 🟢

> 🖼️ Imagen renderizada: [`img/04-clases-clinical.png`](img/04-clases-clinical.png) · vectorial: [`img/04-clases-clinical.svg`](img/04-clases-clinical.svg)

![Diagrama de clases clinical-service](img/04-clases-clinical.png)

```mermaid
classDiagram
    class Patient {
        +UUID id
        +UUID user_id  «unique»
        +date birth_date
        +str sex
        +str diagnosis_category
        +str pseudonym_id  «unique»
        +datetime created_at
    }

    class Clinician {
        +UUID id
        +UUID user_id  «unique»
        +str license_number  «unique»
        +str specialty
        +datetime created_at
    }

    class ClinicalRelationship {
        +UUID id
        +UUID clinician_id  «FK»
        +UUID patient_id  «FK»
        +datetime started_at
        +datetime ended_at
    }

    class TherapyPlan {
        +UUID id
        +UUID patient_id  «FK»
        +UUID clinician_id  «FK»
        +date start_date
        +date end_date
        +str status = "active"
        +datetime created_at
    }

    class Exercise {
        +UUID id
        +str name
        +str phoneme
        +int level = 1
    }

    class ExerciseVersion {
        +UUID id
        +UUID exercise_id  «FK»
        +int version = 1
        +str prompt_text
        +str reference_audio_key
        +datetime published_at
    }

    class Prescription {
        +UUID id
        +UUID plan_id  «FK»
        +UUID exercise_version_id  «FK»
        +int frequency_per_week
        +int target_attempts
    }

    class TherapySession {
        +UUID id
        +UUID patient_id  «FK»
        +datetime started_at
        +datetime ended_at
    }

    class Attempt {
        +UUID id
        +UUID session_id  «FK»
        +UUID exercise_version_id  «FK»
        +str audio_key
        +str status = "pending"
        +datetime submitted_at
    }

    Clinician "1" --> "0..*" ClinicalRelationship
    Patient   "1" --> "0..*" ClinicalRelationship
    Clinician "1" --> "0..*" TherapyPlan
    Patient   "1" --> "0..*" TherapyPlan
    TherapyPlan "1" --> "0..*" Prescription
    Exercise "1" --> "0..*" ExerciseVersion
    ExerciseVersion "1" --> "0..*" Prescription
    Patient "1" --> "0..*" TherapySession
    TherapySession "1" --> "0..*" Attempt
    ExerciseVersion "1" --> "0..*" Attempt
```

**Notas de diseño:**
- `Patient.user_id` y `Clinician.user_id` referencian al `User` del `identity-service`
  (relación **entre servicios**, sin FK física — el aislamiento por esquema lo impide por diseño).
- Los enumerados están tipados en `schemas.py`: `SexEnum`, `PlanStatus`
  (`active/paused/completed/cancelled`), `AttemptStatus` (`pending/reviewed`).
- `ExerciseVersion` implementa el patrón de **versionado**: un `Exercise` conceptual
  con múltiples versiones publicables.

---

## 3. Módulo de Scoring (`scoring-service`) 🟡

> Modelo de dominio **planificado** (v2.1). Aún no existe en el código.

```mermaid
classDiagram
    class Evaluation {
        +UUID id
        +UUID attempt_id  «lógico → clinical.attempts»
        +UUID model_version_id  «lógico → mlops.model_versions»
        +float global_gop
        +str classification  «correcto|aproximacion|incorrecto»
        +datetime scored_at
    }
    class PhonemeResult {
        +UUID id
        +UUID evaluation_id  «FK»
        +str phoneme
        +str expected
        +int start_ms
        +int end_ms
        +float gop_score
        +str classification
        +float confidence
    }
    class FailedJob {
        +UUID id
        +UUID attempt_id  «lógico»
        +str error_class
        +text traceback
        +JSONB payload
        +datetime failed_at
    }
    class ProcessedEvent {
        +UUID event_id  «PK, idempotencia»
        +datetime processed_at
    }

    Evaluation "1" --> "0..*" PhonemeResult : desglosa
```

**Notas:** `scoring-service` se compone de `scoring-api` (FastAPI, SSE) + `scoring-worker`
(Celery). Consume `AttemptCreated`, publica `AttemptScored` / `AttemptFailed`.

---

## 4. Módulo de Analytics (`analytics-service`) 🟡

> Modelo de dominio **planificado** (v2.1). Aún no existe en el código.

```mermaid
classDiagram
    class ConsolidatedMetric {
        +UUID id
        +UUID patient_id  «lógico»
        +date period_start
        +date period_end
        +str phoneme
        +float success_rate
        +float trend_slope
        +int attempts_count
        +JSONB payload_jsonb
    }
    class Alert {
        +UUID id
        +UUID patient_id  «lógico»
        +UUID clinician_id  «lógico»
        +str kind
        +str severity
        +JSONB payload_jsonb
        +datetime created_at
        +datetime acknowledged_at
    }
    class AlertRule {
        +UUID id
        +str scope
        +str kind
        +float threshold
        +int window_days
        +bool active
    }
    class Notification {
        +UUID id
        +UUID user_id  «lógico»
        +str channel  «email|in_app»
        +JSONB payload_jsonb
        +datetime sent_at
        +datetime read_at
    }

    ConsolidatedMetric "1" --> "0..*" Alert : puede generar
    AlertRule "1" --> "0..*" Alert : evalúa
```

**Notas:** consume `AttemptScored`, `AttemptFailed`, `PrescriptionUpdated`; publica
`AlertRaised`. Incluye scheduler (APScheduler) y notificador SMTP.

---

## 5. Módulo de MLOps (`mlops-service`) 🟡

> Modelo de dominio **planificado** (v2.1). ⚠️ **Se descarta Label Studio**: la anotación
> es un módulo propio (UI en la SPA + API en `mlops-service`).

```mermaid
classDiagram
    class CorpusItem {
        +UUID id
        +str audio_key  «MinIO»
        +str pseudonym_id
        +str age_range
        +str sex
        +str diagnosis
        +str target_phoneme
        +str source  «captura|upload»
        +str dvc_hash
    }
    class AnnotationAssignment {
        +UUID id
        +UUID corpus_item_id  «FK»
        +UUID annotator_user_id  «lógico → identity.users»
        +str status  «pending|in_progress|completed»
        +datetime assigned_at
        +datetime completed_at
    }
    class Annotation {
        +UUID id
        +UUID assignment_id  «FK»
        +int phoneme_index
        +str phoneme_expected
        +str label  «correcto|aproximacion|incorrecto»
        +str produced_phoneme  «si label != correcto»
        +text comment
        +datetime created_at
    }
    class Dataset {
        +UUID id
        +str name
        +str version
        +str dvc_hash
        +int item_count
        +str train_split_hash
        +str val_split_hash
        +str test_split_hash
        +datetime created_at
    }
    class ModelVersion {
        +UUID id
        +str mlflow_run_id
        +UUID dataset_id  «FK»
        +str model_type
        +JSONB metrics_jsonb
        +str status  «staging|production|archived»
        +datetime promoted_at
    }

    CorpusItem "1" --> "0..*" AnnotationAssignment : asignado
    AnnotationAssignment "1" --> "0..*" Annotation : "por fonema"
    Dataset "1" --> "0..*" CorpusItem : agrupa
    Dataset "1" --> "0..*" ModelVersion : entrena
```

**Notas:** publica `ModelPromoted` (consumido por `scoring-service`). Empaqueta MLflow
(registry) y DVC (versionado de datasets). El solapamiento de asignaciones a 2+
anotadores habilita el cálculo de IRR (Cohen kappa) por consulta directa al schema.

---

## 6. Vista de contexto entre servicios (relaciones lógicas)

```mermaid
classDiagram
    class User {
        <<identity-service>>
        +UUID id
        +str role
    }
    class Patient {
        <<clinical-service>>
        +UUID user_id
    }
    class Clinician {
        <<clinical-service>>
        +UUID user_id
    }

    User <.. Patient : user_id (lógico, cross-service)
    User <.. Clinician : user_id (lógico, cross-service)

    note for User "La identidad es la fuente de verdad.\nclinical-service referencia por UUID\nsin integridad referencial física."
```

---

## 7. Herramientas recomendadas para graficar diagramas de clases

| Herramienta | Por qué | Costo | Ideal para |
|-------------|---------|-------|------------|
| **Mermaid** (usado aquí) | `classDiagram` como código, versionable, se renderiza en GitHub/VS Code. | Gratis | Repo y tesis |
| **PlantUML** | El estándar UML como código: soporta clases con visibilidad, estereotipos, herencia, cardinalidades formales. Muy valorado académicamente. | Gratis | Diagramas UML rigurosos para el tribunal |
| **StarUML** | Herramienta UML de escritorio completa (todos los diagramas UML 2.x). Exporta a imagen/PDF. | Pago (prueba gratis) | Modelado UML formal y completo |
| **Visual Paradigm** | Suite UML profesional; tiene **edición Community gratuita** para uso académico. Genera código y viceversa. | Freemium | Tesis que exige notación UML estricta |
| **draw.io / diagrams.net** | Tiene plantillas UML; edición visual libre. | Gratis | Diagramas de clases presentables sin escribir código |
| **dbdiagram / DrawSQL** | *(Solo si el foco es el modelo de datos, no las clases de dominio.)* | Freemium | Ver archivo de base de datos |

> **Recomendación para la tesis:** para un diagrama de clases con notación UML formal
> (visibilidad `+/-`, estereotipos `«FK»`, cardinalidades), **PlantUML** o **Visual
> Paradigm (Community)** son la mejor elección académica. Mantené el Mermaid en el repo
> como fuente versionada y generá la lámina UML formal con PlantUML.
