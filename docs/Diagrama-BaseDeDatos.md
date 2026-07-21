# Diagrama de Base de Datos (Modelo Entidad-Relación) — Plataforma PFI

> Diagrama Entidad-Relación (ER) del modelo físico de datos, derivado de los modelos
> ORM SQLAlchemy y del script de inicialización `infra/postgres/init.sql`.
>
> La base es una **única instancia PostgreSQL 16** particionada en **cinco esquemas**
> (uno por microservicio). Cada esquema es accedido por un usuario de base de datos
> dedicado con permisos restringidos (principio de mínimo privilegio). **No hay foreign
> keys cross-schema**: las referencias entre servicios son lógicas (por UUID).
>
> 🟢 = real / implementado · 🟡 = planificado (objetivo v2.1, ver
> [`Arquitectura-Logica.md`](Arquitectura-Logica.md)).
>
> Sintaxis: **Mermaid** (`erDiagram`).

---

## 1. Organización física (esquemas y usuarios)

```mermaid
flowchart TB
    subgraph DB["🗄️ PostgreSQL 16 — base: pfi"]
        direction LR
        S1["schema: identity<br/>👤 identity_user"]
        S2["schema: clinical<br/>👤 clinical_user"]
        S3["schema: scoring<br/>👤 scoring_user"]
        S4["schema: analytics<br/>👤 analytics_user"]
        S5["schema: mlops<br/>👤 mlops_user"]
    end
    note1["Cada usuario tiene GRANT USAGE + CREATE<br/>únicamente sobre su propio esquema"]
    DB -.- note1

    classDef impl fill:#e6f4ea,stroke:#2e7d32;
    classDef empty fill:#f5f5f5,stroke:#bbb,stroke-dasharray:4 4,color:#777;
    class S1,S2 impl;
    class S3,S4,S5 empty;
```

> Los esquemas `scoring`, `analytics` y `mlops` están **preaprovisionados pero vacíos**
> (servicios en estado esqueleto). Las secciones 5–7 documentan su **modelo de datos
> objetivo (v2.1)**, aún no implementado.

---

## 2. Esquema `identity` 🟢

> 🖼️ Imagen renderizada: [`img/05-er-identity.png`](img/05-er-identity.png) · vectorial: [`img/05-er-identity.svg`](img/05-er-identity.svg)

![Diagrama ER esquema identity](img/05-er-identity.png)

```mermaid
erDiagram
    users {
        uuid id PK
        varchar(255) email UK "not null, indexed"
        varchar(255) password_hash "not null"
        varchar(50) role "default 'patient'"
        boolean is_active "default true"
        timestamptz created_at
    }

    refresh_tokens {
        uuid id PK
        uuid user_id "indexed"
        varchar(255) token_hash "SHA-256, not null"
        timestamptz expires_at "not null"
        boolean revoked "default false"
        timestamptz created_at
    }

    invitation_codes {
        uuid id PK
        varchar(12) code UK "PFI-XXXXXXXX, indexed"
        uuid created_by_clinician_id "not null, indexed"
        jsonb pre_filled_data "nullable"
        timestamptz expires_at "not null"
        timestamptz consumed_at "nullable"
        uuid consumed_by_user_id "nullable"
        varchar(20) status "default 'active'"
        timestamptz created_at
    }

    users ||--o{ refresh_tokens : "posee (por user_id, sin FK física)"
    users ||--o{ invitation_codes : "consume (por consumed_by_user_id)"
```

### 2.1. Extensiones objetivo del esquema `identity` 🟡

Entidades planificadas para el alcance v2.1 (consentimientos, tutela de menores y mapa de
seudónimos). Aún **no implementadas**.

```mermaid
erDiagram
    consents {
        uuid id PK
        uuid user_id "→ identity.users.id"
        varchar(50) type "plataforma | clinico | corpus"
        timestamptz signed_at
        timestamptz revoked_at "nullable"
        varchar(20) content_version
    }

    minor_guardianships {
        uuid minor_user_id "→ identity.users.id"
        uuid guardian_user_id "→ identity.users.id"
        timestamptz signed_at
    }

    pseudonym_map {
        varchar(50) pseudonym_id PK "UUID nuevo"
        uuid patient_user_id "→ identity.users.id, cifrado"
    }

    users ||--o{ consents : firma
    users ||--o{ minor_guardianships : "tutor / menor"
    users ||--o| pseudonym_map : "seudonimizado por"
```

> `pseudonym_map` es el **único** punto donde se resuelve seudónimo → paciente; accesible
> solo por `identity-service` para revocación de consentimiento. Al revocarse el
> consentimiento de corpus, `identity-service` emite `CorpusConsentRevoked{pseudonym_id}`.

---

## 3. Esquema `clinical` 🟢

> 🖼️ Imagen renderizada: [`img/06-er-clinical.png`](img/06-er-clinical.png) · vectorial: [`img/06-er-clinical.svg`](img/06-er-clinical.svg)

![Diagrama ER esquema clinical](img/06-er-clinical.png)

```mermaid
erDiagram
    patients {
        uuid id PK
        uuid user_id UK "not null, indexed"
        date birth_date
        varchar(10) sex
        varchar(100) diagnosis_category
        varchar(50) pseudonym_id UK "not null"
        timestamptz created_at
    }

    clinicians {
        uuid id PK
        uuid user_id UK "not null, indexed"
        varchar(100) license_number UK "not null"
        varchar(100) specialty
        timestamptz created_at
    }

    clinical_relationships {
        uuid id PK
        uuid clinician_id FK "not null, indexed"
        uuid patient_id FK "not null, indexed"
        timestamptz started_at
        timestamptz ended_at "nullable"
    }

    therapy_plans {
        uuid id PK
        uuid patient_id FK "not null, indexed"
        uuid clinician_id FK "not null, indexed"
        date start_date "not null"
        date end_date "nullable"
        varchar(20) status "default 'active'"
        timestamptz created_at
    }

    exercises {
        uuid id PK
        varchar(200) name "not null"
        varchar(20) phoneme "nullable"
        integer level "default 1"
    }

    exercise_versions {
        uuid id PK
        uuid exercise_id FK "not null, indexed"
        integer version "default 1"
        text prompt_text "nullable"
        varchar(500) reference_audio_key "MinIO key"
        timestamptz published_at "nullable"
    }

    prescriptions {
        uuid id PK
        uuid plan_id FK "not null, indexed"
        uuid exercise_version_id FK "not null"
        integer frequency_per_week "not null"
        integer target_attempts "not null"
    }

    sessions {
        uuid id PK
        uuid patient_id FK "not null, indexed"
        timestamptz started_at
        timestamptz ended_at "nullable"
    }

    attempts {
        uuid id PK
        uuid session_id FK "not null, indexed"
        uuid exercise_version_id FK "not null"
        varchar(500) audio_key "MinIO key"
        varchar(20) status "default 'pending'"
        timestamptz submitted_at
    }

    clinicians ||--o{ clinical_relationships : atiende
    patients   ||--o{ clinical_relationships : "es atendido en"
    clinicians ||--o{ therapy_plans : prescribe
    patients   ||--o{ therapy_plans : recibe
    therapy_plans ||--o{ prescriptions : contiene
    exercises  ||--o{ exercise_versions : versiona
    exercise_versions ||--o{ prescriptions : "se prescribe en"
    patients   ||--o{ sessions : realiza
    sessions   ||--o{ attempts : "compuesta por"
    exercise_versions ||--o{ attempts : "ejecutada en"
```

> **Objetivo v2.1:** `attempts.status` se convierte en una máquina de estados más rica —
> `pending → processing → scored | failed | rejected_quality` — donde solo
> `clinical-service` escribe `pending` y las transiciones posteriores las gatilla el
> consumo del evento `AttemptScored` (cada servicio escribe únicamente su schema).

---

## 4. Esquema `scoring` 🟡 (planificado)

> 🖼️ Imagen renderizada: [`img/16-er-scoring.png`](img/16-er-scoring.png) · vectorial: [`img/16-er-scoring.svg`](img/16-er-scoring.svg)

![Diagrama ER esquema scoring](img/16-er-scoring.png)

```mermaid
erDiagram
    evaluations {
        uuid id PK
        uuid attempt_id "→ clinical.attempts.id (lógico)"
        uuid model_version_id "→ mlops.model_versions.id (lógico)"
        float global_gop
        varchar(20) classification "correcto|aproximacion|incorrecto"
        timestamptz scored_at
    }

    phoneme_results {
        uuid id PK
        uuid evaluation_id FK
        varchar(10) phoneme
        varchar(10) expected
        integer start_ms
        integer end_ms
        float gop_score
        varchar(20) classification
        float confidence
    }

    failed_jobs {
        uuid id PK
        uuid attempt_id "referencia lógica"
        varchar(100) error_class
        text traceback
        jsonb payload
        timestamptz failed_at
    }

    processed_events {
        uuid event_id PK "idempotencia de consumidores"
        timestamptz processed_at
    }

    evaluations ||--o{ phoneme_results : "produce (N por fonema)"
```

| Entidad | Propósito |
|---------|-----------|
| `evaluations` | Resultado global de un intento: GOP global + clasificación + modelo usado |
| `phoneme_results` | Desglose fonema a fonema: ventana temporal, GOP, clasificación, confianza |
| `failed_jobs` | *Dead-letter*: intentos que fallaron tras los reintentos del worker |
| `processed_events` | Tabla de idempotencia (evita reprocesar el mismo `AttemptCreated`) |

---

## 5. Esquema `analytics` 🟡 (planificado)

> 🖼️ Imagen renderizada: [`img/17-er-analytics.png`](img/17-er-analytics.png) · vectorial: [`img/17-er-analytics.svg`](img/17-er-analytics.svg)

![Diagrama ER esquema analytics](img/17-er-analytics.png)

```mermaid
erDiagram
    consolidated_metrics {
        uuid id PK
        uuid patient_id "referencia lógica"
        date period_start
        date period_end
        varchar(10) phoneme
        float success_rate
        float trend_slope
        integer attempts_count
        jsonb payload_jsonb
    }

    alerts {
        uuid id PK
        uuid patient_id "referencia lógica"
        uuid clinician_id "referencia lógica"
        varchar(50) kind
        varchar(20) severity
        jsonb payload_jsonb
        timestamptz created_at
        timestamptz acknowledged_at "nullable"
    }

    alert_rules {
        uuid id PK
        varchar(50) scope
        varchar(50) kind
        float threshold
        integer window_days
        boolean active
    }

    notifications {
        uuid id PK
        uuid user_id "referencia lógica"
        varchar(20) channel "email|in_app"
        jsonb payload_jsonb
        timestamptz sent_at
        timestamptz read_at "nullable"
    }

    processed_events {
        uuid event_id PK
        timestamptz processed_at
    }

    consolidated_metrics ||--o{ alerts : "puede generar"
    alert_rules ||--o{ alerts : "evalúa"
```

| Entidad | Propósito |
|---------|-----------|
| `consolidated_metrics` | Agregado longitudinal por paciente/fonema/período (tasa de éxito, tendencia) |
| `alerts` | Alertas tempranas al clínico (regresión, estancamiento), con acuse de recibo |
| `alert_rules` | Reglas configurables (umbral, ventana) por admin o clínico |
| `notifications` | Notificaciones enviadas (email / in-app) con estado de lectura |
| `processed_events` | Idempotencia de consumo de eventos |

---

## 6. Esquema `mlops` 🟡 (planificado)

> 🖼️ Imagen renderizada: [`img/18-er-mlops.png`](img/18-er-mlops.png) · vectorial: [`img/18-er-mlops.svg`](img/18-er-mlops.svg)

![Diagrama ER esquema mlops](img/18-er-mlops.png)

```mermaid
erDiagram
    corpus_items {
        uuid id PK
        varchar(500) audio_key "MinIO key"
        varchar(50) pseudonym_id "sin identidad"
        varchar(20) age_range
        varchar(10) sex
        varchar(50) diagnosis "tsh|post_neuro|control"
        varchar(10) target_phoneme
        varchar(30) source "captura|upload"
        varchar(64) dvc_hash "nullable"
    }

    annotation_assignments {
        uuid id PK
        uuid corpus_item_id FK
        uuid annotator_user_id "→ identity.users.id (lógico)"
        varchar(20) status "pending|in_progress|completed"
        timestamptz assigned_at
        timestamptz completed_at "nullable"
    }

    annotations {
        uuid id PK
        uuid assignment_id FK
        integer phoneme_index
        varchar(10) phoneme_expected
        varchar(20) label "correcto|aproximacion|incorrecto"
        varchar(10) produced_phoneme "solo si label != correcto"
        text comment "nullable"
        timestamptz created_at
    }

    datasets {
        uuid id PK
        varchar(100) name
        varchar(20) version
        varchar(64) dvc_hash
        integer item_count
        varchar(64) train_split_hash
        varchar(64) val_split_hash
        varchar(64) test_split_hash
        timestamptz created_at
    }

    model_versions {
        uuid id PK
        varchar(64) mlflow_run_id
        uuid dataset_id FK
        varchar(50) model_type
        jsonb metrics_jsonb
        varchar(20) status "staging|production|archived"
        timestamptz promoted_at "nullable"
    }

    corpus_items ||--o{ annotation_assignments : "asignado en"
    annotation_assignments ||--o{ annotations : "produce (por fonema)"
    corpus_items }o--|| datasets : "pertenece a"
    datasets ||--o{ model_versions : entrena
```

| Entidad | Propósito |
|---------|-----------|
| `corpus_items` | Ítem del corpus anonimizado (audio + metadatos, sin identidad) |
| `annotation_assignments` | Asignación de un ítem a un anotador (solapamiento 2+ para IRR) |
| `annotations` | Juicio fonema a fonema (escala ordinal + fonema producido) — **módulo propio, sin Label Studio** |
| `datasets` | Dataset congelado y versionado con DVC (splits train/val/test) |
| `model_versions` | Versionado de modelos: run MLflow, métricas, estado de promoción |

> ⚠️ **Reingeniería v2.1:** las tablas `label_studio_*` que la versión anterior preveía
> quedan **descartadas**. La anotación se registra directamente en `mlops.annotations`
> mediante el módulo propio; Cohen kappa (IRR) se calcula con una consulta sobre el
> schema, sin exportar/importar JSON de una herramienta externa. MLflow persiste sus
> tablas internas bajo `mlops.mlflow_*`.

---

## 7. Relaciones entre esquemas (cross-service)

> 🖼️ Imagen renderizada: [`img/19-er-global-futuro.png`](img/19-er-global-futuro.png) · vectorial: [`img/19-er-global-futuro.svg`](img/19-er-global-futuro.svg)

![Diagrama ER global cross-schema](img/19-er-global-futuro.png)

```mermaid
erDiagram
    User ||--o{ Consent : firma
    User ||--o{ MinorGuardianship : "tutor de"
    User ||--|| Patient : "es (si role=patient)"
    User ||--|| Clinician : "es (si role=clinician)"
    Clinician ||--o{ ClinicalRelationship : atiende
    Patient ||--o{ ClinicalRelationship : "atendido por"
    ClinicalRelationship ||--o{ TherapyPlan : "tiene plan"
    TherapyPlan ||--o{ Prescription : prescribe
    Prescription }o--|| ExerciseVersion : "apunta a"
    Patient ||--o{ Session : "practica en"
    Session ||--o{ Attempt : contiene
    Attempt }o--|| ExerciseVersion : "ejecuta"
    Attempt ||--o| Evaluation : "evaluado por"
    Evaluation ||--o{ PhonemeResult : "produce"
    Evaluation }o--|| ModelVersion : "usa"
    Patient ||--o{ ConsolidatedMetric : "tiene"
    ConsolidatedMetric ||--o{ Alert : "puede generar"
    CorpusItem ||--o{ AnnotationAssignment : "asignado en"
    AnnotationAssignment }o--|| User : "asignado a (annotator)"
    AnnotationAssignment ||--o{ Annotation : "produce (por fonema)"
    CorpusItem }o--|| Dataset : "pertenece a"
    Dataset ||--o{ ModelVersion : "entrena"
```

Distribución por schema:

| Schema | Entidades principales |
|---|---|
| `identity` | User, Role, Consent, MinorGuardianship, RefreshToken, PseudonymMap |
| `clinical` | Patient, Clinician, ClinicalRelationship, TherapyPlan, Prescription, Exercise, ExerciseVersion, Session, Attempt |
| `scoring` | Evaluation, PhonemeResult, FailedJob, ProcessedEvent |
| `analytics` | ConsolidatedMetric, Alert, AlertRule, Notification, ProcessedEvent |
| `mlops` | CorpusItem, AnnotationAssignment, Annotation, Dataset, ModelVersion, mlflow_* |

> **Importante:** las relaciones entre esquemas de servicios distintos (por ejemplo,
> `scoring.evaluations.attempt_id` → `clinical.attempts.id`, o
> `mlops.annotation_assignments.annotator_user_id` → `identity.users.id`) son **lógicas,
> no físicas**. El aislamiento por esquema y usuario impide declarar FK cross-schema. La
> consistencia se mantiene por eventos (Redis) y por convención de UUID. Esto es
> intencional en arquitecturas de microservicios (*schema/database per service*) y debe
> documentarse como decisión de diseño en la tesis.

---

## 8. Convenciones del modelo

| Convención | Detalle |
|------------|---------|
| **Clave primaria** | `UUID` v4 generado en aplicación (no autoincremental) |
| **Marcas temporales** | `timestamptz` (con zona horaria, en UTC) |
| **Datos semiestructurados** | `JSONB` para `pre_filled_data`, `payload_jsonb`, `metrics_jsonb`, resultados fonémicos heterogéneos |
| **Referencias a binarios** | `audio_key` / `reference_audio_key` guardan la **clave en MinIO**, no el binario |
| **Índices** | Sobre columnas de búsqueda: `email`, `code`, todas las FK, `user_id`, `pseudonym_id` |
| **Integridad referencial** | FK física **solo dentro** del mismo esquema; entre servicios es lógica |
| **Idempotencia** | Tabla `processed_events(event_id, processed_at)` por schema consumidor |

---

## 9. Herramientas recomendadas para graficar el modelo de base de datos

| Herramienta | Por qué | Costo | Ideal para |
|-------------|---------|-------|------------|
| **dbdiagram.io** | *DER como código* (lenguaje DBML), muy rápido, exporta a PNG/PDF/SQL. El favorito para modelos relacionales en tesis. | Gratis / Freemium | El diagrama ER "oficial" de la tesis |
| **DrawSQL** | Editor visual de ER muy prolijo, plantillas y exportación de calidad para láminas. | Freemium | Láminas de defensa presentables |
| **pgAdmin — ERD Tool** | Ya lo tenés en el `docker-compose`. Genera el ER **automáticamente por ingeniería inversa** desde la base real. | Gratis | Validar que el diagrama coincide con la BD real |
| **DBeaver** | Cliente universal; genera diagramas ER desde la conexión, exporta imagen. | Gratis (Community) | Ingeniería inversa rápida del esquema vivo |
| **MySQL Workbench / DBSchema** | Modelado ER visual con notación *crow's foot* formal. | Gratis / Pago | Notación ER clásica y rigurosa |
| **Mermaid** (usado aquí) | `erDiagram` versionable en el repo. | Gratis | Documentación en el repositorio |

> **Recomendación para la tesis:**
> 1. Mantené el **Mermaid** de este archivo como fuente versionada en el repo.
> 2. Para la lámina "oficial" del capítulo de base de datos, usá **dbdiagram.io** (DBML) o **DrawSQL** — producen el ER más limpio y presentable.
> 3. **Validá contra la base real** con la **herramienta ERD de pgAdmin** (que ya está en tu stack) o **DBeaver**: hacé ingeniería inversa del esquema realmente creado y comprobá que coincide con este diagrama (esquemas `identity` y `clinical`). Los esquemas `scoring`, `analytics` y `mlops` reflejan el **modelo objetivo v2.1**, aún no materializado.
