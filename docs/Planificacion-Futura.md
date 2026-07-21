# Planificación de Diseño Futuro — Plataforma PFI

> Este documento reúne los diagramas de **flujo (secuencia)** y **modelo de datos (ER)**
> de **todos los microservicios**, incluyendo los que aún están en estado de esqueleto.
>
> ⚠️ **Naturaleza del documento:** los diagramas se dividen en dos categorías:
> - 🟢 **Real / implementado** — refleja el código existente.
> - 🟡 **Planificado (no implementado)** — es una **propuesta de diseño** para guiar el
>   desarrollo futuro, derivada del dominio descrito en `CLAUDE.md`. Las entidades,
>   endpoints y eventos aquí propuestos **aún no existen en el código** y deben validarse
>   antes de construirse.
>
> Imágenes en `docs/img/` (PNG alta resolución + SVG vectorial).

---

## 1. Flujos de los servicios implementados 🟢

### 1.1. Flujo de autenticación (identity-service) — real

![Flujo de autenticación](img/11-flujo-auth.png)

Cubre login, refresh con rotación de tokens (single-use) y logout. Refleja el código real
de `identity-service/app/main.py`.

### 1.2. Flujo de terapia (clinical-service) — real + gancho futuro

![Flujo de terapia](img/12-flujo-clinical.png)

Preparación de la terapia (plan, ejercicio, versión) y ejecución de la sesión (sesión →
intento). El bloque amarillo marca la parte **planificada**: la carga real del audio a
MinIO y la publicación del evento `AttemptSubmitted` hacia scoring-service.

---

## 2. scoring-service 🟡 (planificado)

### 2.1. Flujo de evaluación

![Flujo de scoring](img/13-flujo-scoring.png)

### 2.2. Modelo de datos propuesto

![ER scoring](img/16-er-scoring.png)

| Entidad | Propósito |
|---------|-----------|
| `scoring_jobs` | Cola de trabajos de evaluación con estado y reintentos (idempotencia/resiliencia) |
| `scores` | Resultado de la evaluación: puntuación global + desglose fonémico (`JSONB`) + modelo usado |

**Eventos:** consume `AttemptSubmitted`, publica `AttemptScored`.

---

## 3. analytics-service 🟡 (planificado)

### 3.1. Flujo de agregación de métricas

![Flujo de analytics](img/14-flujo-analytics.png)

### 3.2. Modelo de datos propuesto

![ER analytics](img/17-er-analytics.png)

| Entidad | Propósito |
|---------|-----------|
| `metric_events` | *Event store* / modelo de lectura: registra los eventos recibidos del bus |
| `progress_snapshots` | Agregados precalculados de progreso por paciente/plan/período |

**Patrón sugerido:** *CQRS/read-model* — analytics no es dueño de los datos primarios,
sino que construye vistas materializadas a partir de eventos.

---

## 4. mlops-service 🟡 (planificado)

### 4.1. Flujo de ciclo de vida del modelo

![Flujo de mlops](img/15-flujo-mlops.png)

### 4.2. Modelo de datos propuesto

![ER mlops](img/18-er-mlops.png)

| Entidad | Propósito |
|---------|-----------|
| `datasets` | Conjuntos de datos de entrenamiento consolidados |
| `labeling_tasks` | Tareas de etiquetado fonémico (integración con **Label Studio**, ya desplegado) |
| `training_runs` | Ejecuciones de entrenamiento con su estado y logs |
| `model_versions` | Versionado de modelos con métricas, artefacto en MinIO y estado de despliegue (`draft/staging/production/archived`) |

**Integración clave:** `scoring-service` consulta la `model_version` en `production`
para inferir; `Label Studio` alimenta las `labeling_tasks`.

---

## 5. Vista integrada a futuro

### 5.1. Arquitectura de eventos completa

![Arquitectura futura](img/20-arquitectura-futura.png)

Muestra el sistema completo con los cinco servicios activos y todos los eventos del bus
Redis (`PatientRegisteredWithInvitation`, `AttemptSubmitted`, `SessionCompleted`,
`AttemptScored`) más las interacciones con MinIO y Label Studio.

### 5.2. Modelo de datos global (relaciones lógicas entre esquemas)

![ER global futuro](img/19-er-global-futuro.png)

Vista simplificada de cómo se relacionan **lógicamente** las entidades clave de los cinco
esquemas. Recordá que entre servicios **no hay FK físicas** (patrón *database per
service*): la consistencia se mantiene por eventos y convención de UUID.

---

## 6. Eventos del bus Redis (contrato propuesto)

| Evento | Publica | Consume | Estado |
|--------|---------|---------|--------|
| `PatientRegisteredWithInvitation` | identity | clinical | 🟢 Implementado |
| `AttemptSubmitted` | clinical | scoring | 🟡 Planificado |
| `SessionCompleted` | clinical | analytics | 🟡 Planificado |
| `AttemptScored` | scoring | clinical, analytics | 🟡 Planificado |

> **Recomendación de diseño (deuda técnica ya identificada):** el Pub/Sub actual de Redis
> no garantiza entrega. Antes de construir estos flujos, evaluar **Redis Streams** o un
> *broker* con persistencia (RabbitMQ/Kafka) y el patrón *outbox* para no perder eventos.

---

## 7. Índice completo de imágenes

| # | Archivo | Tipo | Estado |
|---|---------|------|--------|
| 01 | `01-arquitectura` | Arquitectura general | 🟢 |
| 02 | `02-flujo-invitacion` | Secuencia | 🟢 |
| 03 | `03-clases-identity` | Clases | 🟢 |
| 04 | `04-clases-clinical` | Clases | 🟢 |
| 05 | `05-er-identity` | ER | 🟢 |
| 06 | `06-er-clinical` | ER | 🟢 |
| 07 | `07-scoring-service` | Estructura/alcance | 🟡 |
| 08 | `08-analytics-service` | Estructura/alcance | 🟡 |
| 09 | `09-mlops-service` | Estructura/alcance | 🟡 |
| 10 | `10-estado-microservicios` | Estado global | Mixto |
| 11 | `11-flujo-auth` | Secuencia | 🟢 |
| 12 | `12-flujo-clinical` | Secuencia | 🟢+🟡 |
| 13 | `13-flujo-scoring` | Secuencia | 🟡 |
| 14 | `14-flujo-analytics` | Secuencia | 🟡 |
| 15 | `15-flujo-mlops` | Secuencia | 🟡 |
| 16 | `16-er-scoring` | ER | 🟡 |
| 17 | `17-er-analytics` | ER | 🟡 |
| 18 | `18-er-mlops` | ER | 🟡 |
| 19 | `19-er-global-futuro` | ER integrado | 🟡 |
| 20 | `20-arquitectura-futura` | Arquitectura | 🟢+🟡 |

*Cada entrada existe en `.png` (3x) y `.svg` (vectorial) dentro de `docs/img/`.*
