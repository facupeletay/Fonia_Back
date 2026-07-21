# Diagrama de Base de Datos (Modelo Entidad-Relación) — Plataforma PFI

> Diagrama Entidad-Relación (ER) del modelo físico de datos, derivado de los modelos
> ORM SQLAlchemy y del script de inicialización `infra/postgres/init.sql`.
>
> La base es una **única instancia PostgreSQL 16** particionada en **cinco esquemas**
> (uno por microservicio). Cada esquema es accedido por un usuario de base de datos
> dedicado con permisos restringidos (principio de mínimo privilegio).
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
> (servicios en estado esqueleto).

---

## 2. Esquema `identity`

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

---

## 3. Esquema `clinical`

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

---

## 4. Relaciones entre esquemas (cross-service)

```mermaid
erDiagram
    users ||..o{ patients : "user_id (lógico)"
    users ||..o{ clinicians : "user_id (lógico)"

    users {
        uuid id PK
    }
    patients {
        uuid user_id "→ identity.users.id"
    }
    clinicians {
        uuid user_id "→ identity.users.id"
    }
```

> **Importante:** las relaciones entre `identity.users` y `clinical.patients/clinicians`
> son **lógicas, no físicas**. El aislamiento por esquema y usuario impide declarar una
> FK entre esquemas de distintos servicios. La consistencia se mantiene por eventos
> (Redis) y por convención de UUID. Esto es intencional en arquitecturas de microservicios
> (*database per service*) y debe documentarse como decisión de diseño en la tesis.

---

## 5. Convenciones del modelo

| Convención | Detalle |
|------------|---------|
| **Clave primaria** | `UUID` v4 generado en aplicación (no autoincremental) |
| **Marcas temporales** | `timestamptz` (con zona horaria, en UTC) |
| **Datos semiestructurados** | `JSONB` para `pre_filled_data` (flexibilidad de esquema) |
| **Referencias a binarios** | `audio_key` / `reference_audio_key` guardan la **clave en MinIO**, no el binario |
| **Índices** | Sobre columnas de búsqueda: `email`, `code`, todas las FK, `user_id`, `pseudonym_id` |
| **Integridad referencial** | FK física **solo dentro** del mismo esquema; entre servicios es lógica |

---

## 6. Herramientas recomendadas para graficar el modelo de base de datos

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
> 3. **Validá contra la base real** con la **herramienta ERD de pgAdmin** (que ya está en tu stack) o **DBeaver**: hacé ingeniería inversa del esquema realmente creado y comprobá que coincide con este diagrama. Eso le da rigor de "modelo verificado" a tu tesis.
