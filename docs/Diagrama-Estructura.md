# Diagrama de Estructura y Arquitectura — Plataforma PFI

> Diagrama de arquitectura de despliegue (*deployment / component diagram*) que
> representa la estructura del sistema: frontend, microservicios, infraestructura
> compartida, canales de comunicación y límites de aislamiento.
>
> **Versión de arquitectura: 2.1 (Julio 2026)** — reingeniería del subsistema de
> anotación: se descarta **Label Studio** y se adopta un **módulo de anotación propio**
> integrado en la SPA + `mlops-service`. Ver documento canónico
> [`Arquitectura-Logica.md`](Arquitectura-Logica.md).
>
> Sintaxis: **Mermaid** (se renderiza en GitHub, GitLab, VS Code con extensión, Obsidian, etc.).

---

## 1. Vista general de la arquitectura (objetivo v2.1)

> 🖼️ Imagen renderizada: [`img/01-arquitectura.png`](img/01-arquitectura.png) · vectorial: [`img/01-arquitectura.svg`](img/01-arquitectura.svg)

![Diagrama de arquitectura general](img/01-arquitectura.png)

```mermaid
flowchart TB
    Cliente(["🖥️ React SPA<br/>(Vite + Tailwind + Zustand)"])

    subgraph Gateway["🚪 API Gateway"]
        TF["Traefik v3<br/>:80 / :8080<br/>Enrutamiento por PathPrefix"]
    end

    subgraph Servicios["⚙️ Capa de Microservicios (perfil: services)"]
        ID["identity-service<br/>:8001 · /api/identity<br/>JWT RS256 + JWKS"]
        CL["clinical-service<br/>:8002 · /api/clinical"]
        SC["scoring-service<br/>:8003 · /api/scoring<br/>API (SSE) + Celery worker<br/>(esqueleto)"]
        AN["analytics-service<br/>:8004 · /api/analytics<br/>métricas + alertas + notif.<br/>(esqueleto)"]
        ML["mlops-service<br/>:8005 · /api/mlops<br/>anotación propia + MLflow + DVC<br/>(esqueleto)"]
    end

    subgraph Infra["🗄️ Infraestructura compartida (siempre activa)"]
        PG[("PostgreSQL 16<br/>1 esquema/usuario por servicio")]
        RD[("Redis 7<br/>Pub/Sub + broker Celery")]
        MN[("MinIO<br/>Object Storage S3<br/>audios · corpus · modelos · DVC")]
        MLF["MLflow Tracking<br/>(dentro de mlops)"]
        PGA["pgAdmin<br/>:5050"]
    end

    EMAIL["📧 Email externo<br/>(SMTP / SES)"]

    Cliente -->|HTTPS| TF
    TF -->|/api/identity| ID
    TF -->|/api/clinical| CL
    TF -->|/api/scoring<br/>SSE feedback| SC
    TF -->|/api/analytics| AN
    TF -->|/api/mlops| ML

    CL -.->|publish AttemptCreated<br/>PrescriptionUpdated| RD
    SC -.->|sub AttemptCreated<br/>pub AttemptScored / AttemptFailed| RD
    AN -.->|sub AttemptScored / PrescriptionUpdated<br/>pub AlertRaised| RD
    ML -.->|pub ModelPromoted| RD
    ID -.->|pub CorpusConsentRevoked| RD

    ID --> PG
    CL --> PG
    SC --> PG
    AN --> PG
    ML --> PG
    MLF --> PG

    CL --> MN
    SC --> MN
    ML --> MN
    MLF --> MN

    AN --> EMAIL

    CL -.valida JWT offline JWKS.-> ID
    SC -.valida JWT offline JWKS.-> ID
    AN -.valida JWT offline JWKS.-> ID
    ML -.valida JWT offline JWKS.-> ID

    classDef stub fill:#f5f5f5,stroke:#bbb,stroke-dasharray:4 4,color:#777;
    classDef done fill:#e6f4ea,stroke:#2e7d32,color:#1b5e20;
    classDef infra fill:#e8eef7,stroke:#1565c0,color:#0d47a1;
    class ID,CL done;
    class SC,AN,ML stub;
    class PG,RD,MN,MLF,PGA infra;
```

> **Nota de transición:** en el repositorio actual el `docker-compose.yml` todavía
> incluye el contenedor **Label Studio** (usado en la fase exploratoria para prototipar
> el esquema de anotación) y los microservicios `scoring`/`analytics`/`mlops` están en
> estado **esqueleto**. El diagrama representa la **arquitectura objetivo v2.1**: la
> anotación pasa a ser un módulo propio dentro de `mlops-service` + la SPA, y Label
> Studio se retira. Ver [`Arquitectura-Logica.md` §5.2](Arquitectura-Logica.md).

---

## 2. Vista de estructura interna de un microservicio

Todos los servicios comparten la misma estructura de carpetas (patrón homogéneo). El
`scoring-service` agrega, además, un proceso **worker** (Celery) que comparte codebase y
schema con la API.

```mermaid
flowchart TB
    subgraph SVC["services/&lt;name&gt;/"]
        DF["Dockerfile"]
        RQ["requirements.txt"]
        subgraph APP["app/"]
            CFG["config.py<br/>Settings (env vars)"]
            DB["database.py<br/>Engine + SessionLocal + Base"]
            MOD["models.py<br/>ORM SQLAlchemy (schema-namespaced)"]
            SCH["schemas.py<br/>DTOs Pydantic (request/response)"]
            MN["main.py<br/>App FastAPI + rutas"]
            EV["events.py<br/>Listener Redis Pub/Sub (opcional)"]
            AU["auth.py<br/>Helpers JWT / verificación JWKS"]
            WK["worker.py<br/>Celery worker (solo scoring)"]
        end
    end

    MN --> CFG
    MN --> DB
    MN --> MOD
    MN --> SCH
    MN --> EV
    MN --> AU
    MOD --> DB
    EV --> DB
    AU --> CFG
    WK --> MOD
    WK --> EV

    classDef opt fill:#fff8e1,stroke:#f9a825,color:#795548;
    class EV,AU,WK opt;
```

---

## 3. Flujo de comunicación por evento (registro por invitación) 🟢

> 🖼️ Imagen renderizada: [`img/02-flujo-invitacion.png`](img/02-flujo-invitacion.png) · vectorial: [`img/02-flujo-invitacion.svg`](img/02-flujo-invitacion.svg)

![Diagrama de secuencia del flujo de invitación](img/02-flujo-invitacion.png)

```mermaid
sequenceDiagram
    autonumber
    actor P as Paciente
    participant TF as Traefik
    participant ID as identity-service
    participant RD as Redis
    participant CL as clinical-service
    participant PG as PostgreSQL

    P->>TF: POST /api/identity/auth/register-with-code
    TF->>ID: enruta petición
    ID->>PG: crea User + marca código consumido
    ID->>RD: publish("identity.events", PatientRegisteredWithInvitation)
    ID-->>P: 201 Created (UserResponse)
    Note over RD,CL: Comunicación asíncrona
    RD-->>CL: entrega evento (listener en hilo daemon)
    CL->>PG: crea Patient + ClinicalRelationship
```

> Este flujo es **real / implementado** y no cambia con la arquitectura v2.1.

---

## 4. Canales de comunicación (resumen)

| Canal | Tipo | Origen → Destino | Tecnología | Estado |
|-------|------|-------------------|-----------|--------|
| API REST | Síncrono | SPA → Servicio | HTTP vía Traefik | 🟢 |
| Feedback en vivo | Streaming | scoring → SPA | **SSE** (Server-Sent Events) | 🟡 |
| Bus de eventos | Asíncrono | Servicio → Servicio | Redis Pub/Sub | 🟢 (1 evento) / 🟡 (resto) |
| Cola de tareas ML | Asíncrono | clinical → scoring-worker | Redis + Celery | 🟡 |
| Persistencia | — | Servicio → su esquema | PostgreSQL (aislamiento por usuario) | 🟢 |
| Object storage | — | clinical/scoring/mlops → objetos | MinIO (API S3) | 🟢 (provisto) |
| Autenticación | Sin estado | Cualquier servicio | JWT — **HS256 hoy → RS256 + JWKS objetivo** | 🟢 → 🟡 |

> **Autenticación — nota de evolución:** el código actual firma y valida JWT con
> **HS256 y clave secreta compartida**. La arquitectura objetivo v2.1 migra a **RS256
> con JWKS**: `identity-service` firma con clave privada y publica la clave pública en
> `GET /.well-known/jwks.json`; cada servicio valida offline sin round-trip.

---

## 5. Herramientas recomendadas para graficar este diagrama

Este es un **diagrama de arquitectura / despliegue / componentes**. Recomendaciones ordenadas por conveniencia para el proyecto:

| Herramienta | Por qué | Costo | Ideal para |
|-------------|---------|-------|------------|
| **Mermaid** (ya usado aquí) | Diagramas como código, versionable en Git, se renderiza solo en GitHub/VS Code. Cero mantenimiento visual. | Gratis / Open source | Incluir en la tesis y en el repo |
| **draw.io / diagrams.net** | Editor visual libre, exporta a PNG/SVG/PDF, tiene *stencils* de AWS/Docker/redes. Ideal para el diagrama "bonito" de la defensa. | Gratis | Láminas y anexos de la tesis |
| **Excalidraw** | Estilo "a mano alzada", muy claro para explicar arquitectura sin sobrecargar. Integración con VS Code. | Gratis | Explicaciones y pizarra conceptual |
| **PlantUML** | Diagramas de despliegue/componentes UML formales como código. | Gratis | Si tu tribunal exige notación UML estricta |
| **Structurizr** | Basado en el modelo **C4** (Context, Container, Component). El estándar moderno para documentar arquitecturas de microservicios. | Freemium | Elevar el nivel académico del capítulo de arquitectura |

> **Recomendación para la tesis:** mantené el **Mermaid** en el repositorio (trazable y versionado) y generá una versión pulida en **draw.io** para las láminas impresas. Si querés impresionar al tribunal en la parte de arquitectura, adoptá el **modelo C4** con Structurizr o con la librería `C4-PlantUML`. El documento canónico [`Arquitectura-Logica.md`](Arquitectura-Logica.md) ya incluye los diagramas C4 de nivel 1 (contexto) y 2 (contenedores).
