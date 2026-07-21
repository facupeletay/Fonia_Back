# Diagramas por Microservicio — Plataforma PFI

> Vista individual de cada uno de los cinco microservicios del backend, con su estado
> real de implementación. Los diagramas de clases y ER detallados de los servicios
> implementados están en `Diagrama-Clases.md` y `Diagrama-BaseDeDatos.md`.
>
> Todas las imágenes están en `docs/img/` en formato **PNG** (alta resolución) y
> **SVG** (vectorial, para impresión sin pérdida).

---

## 0. Estado global de los microservicios

![Estado de los microservicios](img/10-estado-microservicios.png)

| Servicio | Puerto | Estado | Tablas |
|----------|--------|--------|--------|
| `identity-service` | 8001 | ✅ Implementado | `users`, `refresh_tokens`, `invitation_codes` |
| `clinical-service` | 8002 | ✅ Implementado | `patients`, `clinicians`, `clinical_relationships`, `therapy_plans`, `exercises`, `exercise_versions`, `prescriptions`, `sessions`, `attempts` |
| `scoring-service` | 8003 | 🟡 Esqueleto | — (esquema vacío) |
| `analytics-service` | 8004 | 🟡 Esqueleto | — (esquema vacío) |
| `mlops-service` | 8005 | 🟡 Esqueleto | — (esquema vacío) |

---

## 1. identity-service ✅

Servicio de identidad, autenticación y códigos de invitación. Modelo de datos completo.

- **Diagrama de clases:** ver [`Diagrama-Clases.md` §1](Diagrama-Clases.md) → `img/03-clases-identity.png`
- **Diagrama ER:** ver [`Diagrama-BaseDeDatos.md` §2](Diagrama-BaseDeDatos.md) → `img/05-er-identity.png`

![Clases identity-service](img/03-clases-identity.png)

---

## 2. clinical-service ✅

Servicio de historia clínica, planes de terapia, ejercicios y sesiones. Modelo de datos completo.

- **Diagrama de clases:** ver [`Diagrama-Clases.md` §2](Diagrama-Clases.md) → `img/04-clases-clinical.png`
- **Diagrama ER:** ver [`Diagrama-BaseDeDatos.md` §3](Diagrama-BaseDeDatos.md) → `img/06-er-clinical.png`

![Clases clinical-service](img/04-clases-clinical.png)

---

## 3. scoring-service 🟡

> **Estado actual:** esqueleto. El código contiene únicamente la app FastAPI con el
> endpoint `/health`; **no tiene `models.py` ni `schemas.py`** y su esquema de base de
> datos (`scoring`) está vacío. El diagrama documenta el estado real y el alcance
> planificado (aún **no implementado**).

![scoring-service estado y alcance](img/07-scoring-service.png)

**Responsabilidad prevista:** evaluar automáticamente la pronunciación de los intentos
(*attempts*) de audio, generando una puntuación fonémica, consumiendo los audios desde
MinIO y publicando el resultado en el bus de eventos.

---

## 4. analytics-service 🟡

> **Estado actual:** esqueleto (solo `/health`, esquema `analytics` vacío). El diagrama
> muestra el estado real y el alcance planificado (**no implementado**).

![analytics-service estado y alcance](img/08-analytics-service.png)

**Responsabilidad prevista:** consolidar métricas de progreso terapéutico por paciente
y por plan, alimentándose de eventos del sistema (p. ej. intentos evaluados, sesiones
completadas).

---

## 5. mlops-service 🟡

> **Estado actual:** esqueleto (solo `/health`, esquema `mlops` vacío). Nota: el usuario
> de base de datos `mlops_user` ya es utilizado por **Label Studio** (etiquetado
> fonémico) que sí está desplegado en la infraestructura. El diagrama muestra el estado
> real y el alcance planificado (**no implementado**).

![mlops-service estado y alcance](img/09-mlops-service.png)

**Responsabilidad prevista:** gestionar el ciclo de vida de los modelos de evaluación
(registro, versionado, artefactos en MinIO) y el circuito de etiquetado de datos que
alimenta el entrenamiento.

---

## Índice de imágenes generadas

| # | Archivo | Descripción |
|---|---------|-------------|
| 01 | `img/01-arquitectura.*` | Arquitectura general del sistema |
| 02 | `img/02-flujo-invitacion.*` | Diagrama de secuencia del flujo de invitación |
| 03 | `img/03-clases-identity.*` | Diagrama de clases — identity-service |
| 04 | `img/04-clases-clinical.*` | Diagrama de clases — clinical-service |
| 05 | `img/05-er-identity.*` | Modelo ER — esquema identity |
| 06 | `img/06-er-clinical.*` | Modelo ER — esquema clinical |
| 07 | `img/07-scoring-service.*` | Estado y alcance — scoring-service |
| 08 | `img/08-analytics-service.*` | Estado y alcance — analytics-service |
| 09 | `img/09-mlops-service.*` | Estado y alcance — mlops-service |
| 10 | `img/10-estado-microservicios.*` | Estado global de los 5 microservicios |

*Cada entrada existe en `.png` (alta resolución 3x) y `.svg` (vectorial).*
