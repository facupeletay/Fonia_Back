# Diagrama de Estructura y Arquitectura — Plataforma PFI

> Diagrama de arquitectura de despliegue (*deployment / component diagram*) que
> representa la estructura del backend: microservicios, infraestructura compartida,
> canales de comunicación y límites de aislamiento.
>
> Sintaxis: **Mermaid** (se renderiza en GitHub, GitLab, VS Code con extensión, Obsidian, etc.).

---

## 1. Vista general de la arquitectura

> 🖼️ Imagen renderizada: [`img/01-arquitectura.png`](img/01-arquitectura.png) · vectorial: [`img/01-arquitectura.svg`](img/01-arquitectura.svg)

![Diagrama de arquitectura general](img/01-arquitectura.png)

```mermaid
flowchart TB
    Cliente(["🖥️ Cliente<br/>(Web / App)"])

    subgraph Gateway["🚪 API Gateway"]
        TF["Traefik v3<br/>:80 / :8080<br/>Enrutamiento por PathPrefix"]
    end

    subgraph Servicios["⚙️ Capa de Microservicios (perfil: services)"]
        ID["identity-service<br/>:8001<br/>/api/identity"]
        CL["clinical-service<br/>:8002<br/>/api/clinical"]
        SC["scoring-service<br/>:8003<br/>/api/scoring<br/>(esqueleto)"]
        AN["analytics-service<br/>:8004<br/>/api/analytics<br/>(esqueleto)"]
        ML["mlops-service<br/>:8005<br/>/api/mlops<br/>(esqueleto)"]
    end

    subgraph Infra["🗄️ Infraestructura compartida (siempre activa)"]
        PG[("PostgreSQL 16<br/>1 esquema/usuario por servicio")]
        RD[("Redis 7<br/>Bus de eventos Pub/Sub")]
        MN[("MinIO<br/>Object Storage S3<br/>audios + modelos")]
        LS["Label Studio<br/>:8090<br/>Etiquetado fonémico"]
        PGA["pgAdmin<br/>:5050"]
    end

    Cliente -->|HTTPS| TF
    TF -->|/api/identity| ID
    TF -->|/api/clinical| CL
    TF -->|/api/scoring| SC
    TF -->|/api/analytics| AN
    TF -->|/api/mlops| ML

    ID -.->|publish<br/>identity.events| RD
    RD -.->|subscribe| CL

    ID --> PG
    CL --> PG
    SC --> PG
    AN --> PG
    ML --> PG

    SC --> MN
    ML --> MN
    LS --> PG
    PGA --> PG

    classDef stub fill:#f5f5f5,stroke:#bbb,stroke-dasharray:4 4,color:#777;
    classDef done fill:#e6f4ea,stroke:#2e7d32,color:#1b5e20;
    classDef infra fill:#e8eef7,stroke:#1565c0,color:#0d47a1;
    class ID,CL done;
    class SC,AN,ML stub;
    class PG,RD,MN,LS,PGA infra;
```

---

## 2. Vista de estructura interna de un microservicio

Todos los servicios comparten la misma estructura de carpetas (patrón homogéneo):

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
            EV["events.py<br/>Listener Redis (opcional)"]
            AU["auth.py<br/>Helpers JWT (solo identity)"]
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

    classDef opt fill:#fff8e1,stroke:#f9a825,color:#795548;
    class EV,AU opt;
```

---

## 3. Flujo de comunicación por evento (registro por invitación)

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

---

## 4. Canales de comunicación (resumen)

| Canal | Tipo | Origen → Destino | Tecnología |
|-------|------|-------------------|-----------|
| API REST | Síncrono | Cliente → Servicio | HTTP vía Traefik |
| Bus de eventos | Asíncrono | identity → clinical | Redis Pub/Sub (`identity.events`) |
| Persistencia | — | Servicio → su esquema | PostgreSQL (aislamiento por usuario) |
| Object storage | — | scoring/mlops → objetos | MinIO (API S3) |
| Autenticación | Sin estado | Cualquier servicio | JWT HS256 (clave compartida) |

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

> **Recomendación para la tesis:** mantené el **Mermaid** en el repositorio (trazable y versionado) y generá una versión pulida en **draw.io** para las láminas impresas. Si querés impresionar al tribunal en la parte de arquitectura, adoptá el **modelo C4** con Structurizr o con la librería `C4-PlantUML`.
