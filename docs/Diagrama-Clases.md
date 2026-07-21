# Diagrama de Clases (UML) — Plataforma PFI

> Diagrama de clases UML que representa el modelo de dominio del backend, derivado de
> los modelos ORM SQLAlchemy (`models.py`) y los esquemas Pydantic (`schemas.py`) de
> cada microservicio.
>
> Sintaxis: **Mermaid** (`classDiagram`). Se muestran atributos, tipos y relaciones.
> Se omiten getters/setters por tratarse de entidades de datos (POPO/ORM).

---

## 1. Módulo de Identidad (`identity-service`)

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

## 2. Módulo Clínico (`clinical-service`)

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

## 3. Vista de contexto entre servicios (relaciones lógicas)

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

## 4. Herramientas recomendadas para graficar diagramas de clases

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
