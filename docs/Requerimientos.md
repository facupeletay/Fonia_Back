# Especificación de Requerimientos de Software (ERS)

## Plataforma PFI — Sistema de Terapia del Habla Asistida

> Documento de Especificación de Requerimientos de Software elaborado siguiendo los
> lineamientos del estándar **IEEE 830 / ISO/IEC/IEEE 29148** y clasificando los
> atributos de calidad según **ISO/IEC 25010 (SQuaRE)**.
>
> Los requerimientos aquí presentados fueron **extraídos por ingeniería inversa** a
> partir del código fuente del backend (microservicios FastAPI + PostgreSQL). Cada
> requerimiento está trazado a su evidencia en el código mediante la columna *Origen*.

| | |
|---|---|
| **Proyecto** | PFI — Proyecto Final Integrador |
| **Dominio** | Plataforma de terapia del habla (speech-therapy) |
| **Arquitectura** | Microservicios orquestados con Docker Compose y API Gateway (Traefik) |
| **Alcance del documento** | Backend (capa de servicios y persistencia) |
| **Fecha** | 2026-07-16 |
| **Versión** | 1.0 |

---

## 1. Introducción

### 1.1. Propósito

Este documento especifica los requerimientos funcionales y no funcionales del backend
de la plataforma **PFI**, un sistema distribuido cuyo objetivo es asistir procesos de
terapia del habla mediante la gestión de pacientes, planes terapéuticos, ejercicios
fonémicos y la captura de audio para su posterior evaluación automática mediante un
pipeline de *Machine Learning*.

La especificación sirve como marco de referencia para la validación del sistema
construido, la trazabilidad de las decisiones de diseño y la planificación de las
funcionalidades pendientes.

### 1.2. Alcance del sistema

El backend está organizado en **cinco dominios de negocio**, cada uno materializado
como un microservicio independiente con su propio esquema de base de datos:

| Servicio | Responsabilidad | Estado |
|----------|-----------------|--------|
| `identity-service` | Autenticación, gestión de usuarios y códigos de invitación | Implementado |
| `clinical-service` | Historia clínica, planes de terapia, ejercicios y sesiones | Implementado |
| `scoring-service` | Evaluación automática de la pronunciación (fonémica) | Esqueleto |
| `analytics-service` | Métricas de progreso y reportes | Esqueleto |
| `mlops-service` | Ciclo de vida de los modelos de ML y etiquetado de datos | Esqueleto |

### 1.3. Definiciones, acrónimos y abreviaturas

| Término | Definición |
|---------|-----------|
| **RF** | Requerimiento Funcional |
| **RNF** | Requerimiento No Funcional |
| **JWT** | *JSON Web Token*, mecanismo de autenticación sin estado |
| **Fonema** | Unidad mínima distintiva del sistema fonológico de una lengua |
| **Clínico** | Profesional (fonoaudiólogo/logopeda) que administra la terapia |
| **Paciente** | Usuario final que ejecuta los ejercicios de terapia |
| **Intento (*Attempt*)** | Grabación de audio de un paciente ejecutando un ejercicio |
| **Pseudónimo** | Identificador anónimo del paciente para disociar datos clínicos de la identidad |
| **Pub/Sub** | Patrón de mensajería *Publish/Subscribe* (mediado por Redis) |
| **Bus de eventos** | Canal asíncrono de comunicación entre microservicios |

### 1.4. Convenciones de identificación

Cada requerimiento se identifica con un código `RF-<MOD>-NNN` / `RNF-<CAT>-NNN`,
donde `<MOD>` denota el módulo funcional y `<CAT>` la categoría de calidad ISO 25010.
La prioridad se expresa mediante la técnica **MoSCoW** (*Must / Should / Could / Won't*).

---

## 2. Descripción general

### 2.1. Perspectiva del producto

El sistema adopta un estilo arquitectónico de **microservicios desacoplados** que se
comunican a través de tres canales bien diferenciados:

1. **API REST síncrona** — expuesta al exterior a través del *API Gateway* (Traefik),
   que enruta las peticiones por prefijo de ruta (`/api/<servicio>`).
2. **Bus de eventos asíncrono** — mediante Redis Pub/Sub para la coordinación entre
   servicios sin acoplamiento directo.
3. **Persistencia aislada** — una única instancia PostgreSQL con **un esquema y un
   usuario de base de datos por servicio**, garantizando el aislamiento de datos.

La autenticación es **descentralizada y sin estado**: `identity-service` emite los
tokens JWT y cada servicio los verifica de forma autónoma con una clave secreta
compartida, evitando un punto único de fallo por proxy de autenticación.

### 2.2. Roles de usuario

| Rol | Descripción | Evidencia |
|-----|-------------|-----------|
| **Paciente** (`patient`) | Usuario que ejecuta los ejercicios; rol por defecto | `models.py` (`role default="patient"`) |
| **Clínico** (`clinician`) | Profesional que crea invitaciones, planes y ejercicios | Flujo de invitaciones y relaciones clínicas |

### 2.3. Restricciones de diseño

- El backend está construido sobre **FastAPI 0.115**, **SQLAlchemy 2.0** y **PostgreSQL 16**.
- Los tokens de acceso usan el algoritmo **HS256** con una vida útil de **15 minutos**.
- El almacenamiento de objetos (audio, artefactos de modelos) se delega a **MinIO**
  (compatible con la API S3).
- La creación del esquema se realiza en el arranque vía `Base.metadata.create_all()`;
  aún no se emplean migraciones Alembic activas.

---

## 3. Requerimientos Funcionales

### 3.1. Módulo de Identidad (`identity-service`)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RF-ID-001** | El sistema debe permitir el registro directo de un usuario a partir de su correo electrónico, contraseña y rol, devolviendo el usuario creado. | Must | `POST /auth/register` (`main.py:61`) |
| **RF-ID-002** | El sistema debe rechazar el registro de un correo electrónico ya existente, informando el error correspondiente. | Must | `main.py:63-64` |
| **RF-ID-003** | El sistema debe almacenar las contraseñas de forma irreversible mediante un algoritmo de *hashing* con sal (bcrypt), sin persistir nunca la contraseña en texto plano. | Must | `auth.py:6-7` |
| **RF-ID-004** | El sistema debe autenticar a un usuario mediante correo y contraseña, devolviendo un *token* de acceso y un *token* de refresco ante credenciales válidas. | Must | `POST /auth/login` (`main.py:75`) |
| **RF-ID-005** | El sistema debe responder con un error de autenticación genérico (sin distinguir si el fallo es por usuario inexistente o contraseña incorrecta) para no revelar la existencia de cuentas. | Should | `main.py:78-79` |
| **RF-ID-006** | El sistema debe permitir renovar la sesión intercambiando un *token* de refresco válido por un nuevo par de *tokens*. | Must | `POST /auth/refresh` (`main.py:94`) |
| **RF-ID-007** | Los *tokens* de refresco deben ser de **un solo uso**: al utilizarse deben revocarse y emitirse uno nuevo (rotación de *tokens*). | Must | `main.py:111-124` |
| **RF-ID-008** | El sistema debe persistir los *tokens* de refresco únicamente como *hash* SHA-256, nunca en claro. | Must | `main.py:86`, `models.py:24` |
| **RF-ID-009** | El sistema debe permitir el cierre de sesión revocando el *token* de refresco asociado. | Must | `POST /auth/logout` (`main.py:128`) |
| **RF-ID-010** | Un clínico debe poder generar un código de invitación único con formato `PFI-XXXXXXXX`, opcionalmente con datos precargados del paciente y una fecha de expiración configurable. | Must | `POST /invitations` (`main.py:170`), `_generate_code` (`main.py:33`) |
| **RF-ID-011** | El sistema debe garantizar la unicidad del código de invitación generado, reintentando la generación ante colisiones. | Should | `main.py:35-38` |
| **RF-ID-012** | Un clínico debe poder consultar el listado de invitaciones que ha generado, ordenadas de la más reciente a la más antigua. | Should | `GET /invitations/clinician/{id}` (`main.py:184`) |
| **RF-ID-013** | El sistema debe permitir validar un código de invitación, devolviendo los datos precargados para agilizar el formulario de registro del paciente. | Must | `POST /invitations/{code}/validate` (`main.py:191`) |
| **RF-ID-014** | El sistema debe rechazar códigos inexistentes, ya consumidos, revocados o expirados, marcando automáticamente como *expirado* aquel cuya fecha de vencimiento haya pasado. | Must | `_get_active_invitation` (`main.py:41-51`) |
| **RF-ID-015** | Un paciente debe poder registrarse mediante un código de invitación válido; al hacerlo, el código se marca como *consumido* y se vincula al usuario creado. | Must | `POST /auth/register-with-code` (`main.py:140`) |
| **RF-ID-016** | Al completarse un registro por invitación, el sistema debe publicar el evento `PatientRegisteredWithInvitation` en el bus de eventos para notificar a los demás servicios. | Must | `main.py:158-163` |
| **RF-ID-017** | Un clínico debe poder revocar una invitación aún activa; el sistema debe impedir la revocación de invitaciones ya consumidas o previamente revocadas. | Should | `DELETE /invitations/{code}` (`main.py:201`) |
| **RF-ID-018** | El sistema debe exponer un *endpoint* de verificación de estado (*health check*) que confirme la disponibilidad del servicio. | Must | `GET /health` (`main.py:57`) |

### 3.2. Módulo Clínico (`clinical-service`)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RF-CL-001** | El sistema debe permitir registrar un paciente asociándolo a un usuario, con fecha de nacimiento, sexo, categoría diagnóstica y un pseudónimo. | Must | `POST /patients` (`main.py:54`) |
| **RF-CL-002** | El sistema debe impedir el registro duplicado de un paciente para un mismo usuario. | Must | `main.py:56-57` |
| **RF-CL-003** | El sistema debe asignar a cada paciente un **pseudónimo único** que permita disociar los datos clínicos de la identidad real (seudonimización). | Must | `models.py:17`, `events.py:32` |
| **RF-CL-004** | El sistema debe permitir consultar los datos de un paciente por su identificador. | Must | `GET /patients/{id}` (`main.py:65`) |
| **RF-CL-005** | El sistema debe permitir registrar un clínico con su número de matrícula (único) y especialidad. | Must | `POST /clinicians` (`main.py:75`) |
| **RF-CL-006** | El sistema debe impedir el registro duplicado de un clínico para un mismo usuario y garantizar la unicidad del número de matrícula. | Must | `main.py:77-78`, `models.py:27` |
| **RF-CL-007** | Un clínico autenticado debe poder consultar el listado de sus pacientes **activos** (relaciones clínicas no finalizadas). | Must | `GET /clinicians/me/patients` (`main.py:86-103`) |
| **RF-CL-008** | El sistema debe mantener la relación clínico–paciente con marcas temporales de inicio y fin, permitiendo modelar el alta y la baja de la relación terapéutica. | Should | `models.py:32-40` |
| **RF-CL-009** | El sistema debe permitir crear un plan de terapia asociado a un paciente y un clínico, con fechas de inicio/fin y un estado (activo, pausado, completado, cancelado). | Must | `POST /therapy-plans` (`main.py:108`), `schemas.py:14-18` |
| **RF-CL-010** | El sistema debe permitir actualizar la fecha de finalización y el estado de un plan de terapia existente. | Should | `PUT /therapy-plans/{id}` (`main.py:117`) |
| **RF-CL-011** | El sistema debe permitir crear y listar un catálogo de ejercicios caracterizados por nombre, fonema objetivo y nivel de dificultad. | Must | `POST/GET /exercises` (`main.py:131-142`) |
| **RF-CL-012** | El sistema debe soportar el **versionado de ejercicios**, permitiendo asociar a un ejercicio distintas versiones con su consigna, audio de referencia y fecha de publicación. | Should | `POST /exercises/{id}/versions` (`main.py:145`) |
| **RF-CL-013** | El sistema debe validar la existencia del ejercicio antes de crear una versión. | Should | `main.py:147-148` |
| **RF-CL-014** | El sistema debe permitir iniciar una sesión de terapia asociada a un paciente existente, validando dicha existencia. | Must | `POST /sessions` (`main.py:158-166`) |
| **RF-CL-015** | El sistema debe permitir registrar un intento (*attempt*) de ejercicio dentro de una sesión, referenciando la versión del ejercicio y la clave del audio grabado. | Must | `POST /attempts` (`main.py:171`) |
| **RF-CL-016** | El sistema debe validar la existencia de la sesión antes de registrar un intento. | Should | `main.py:173-174` |
| **RF-CL-017** | Cada intento debe registrar su estado de revisión (*pending* / *reviewed*), habilitando el circuito de evaluación posterior. | Should | `schemas.py:21-24`, `models.py:107` |
| **RF-CL-018** | El sistema debe modelar la **prescripción** de versiones de ejercicio dentro de un plan, con frecuencia semanal y cantidad de intentos objetivo. | Could | `models.py:78-86` (modelo `Prescription`) |

### 3.3. Módulo de Integración y Eventos (transversal)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RF-EV-001** | El `clinical-service` debe suscribirse al canal `identity.events` y reaccionar al evento `PatientRegisteredWithInvitation`. | Must | `events.py:57-75` |
| **RF-EV-002** | Al recibir el evento de registro, el sistema debe crear automáticamente el registro clínico del paciente sin intervención manual. | Must | `events.py:18-34` |
| **RF-EV-003** | Al recibir el evento, el sistema debe crear automáticamente la relación clínico–paciente que vincula al nuevo paciente con el clínico emisor de la invitación. | Must | `events.py:37-48` |
| **RF-EV-004** | El procesamiento de eventos debe ser **idempotente**: la recepción repetida del mismo evento no debe generar registros duplicados. | Must | `events.py:25-27` |
| **RF-EV-005** | El listener de eventos debe ser resiliente ante la pérdida de conexión con el bus, reintentando la reconexión automáticamente. | Should | `events.py:73-75` |
| **RF-EV-006** | El listener debe ejecutarse en un hilo de fondo (*daemon*) iniciado durante el arranque del servicio, sin bloquear la atención de peticiones HTTP. | Must | `events.py:78-81`, `main.py:29-31` |

### 3.4. Módulos previstos (no implementados)

Los siguientes requerimientos se derivan de la arquitectura declarada (esquemas de base
de datos preaprovisionados, servicios en estado *esqueleto* y objetivo del dominio) y
constituyen el **backlog** de la plataforma.

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RF-SC-001** | El `scoring-service` debe evaluar automáticamente la pronunciación de un intento de audio, produciendo una puntuación fonémica. | Should | Esquema `scoring`, dominio del proyecto |
| **RF-SC-002** | El `scoring-service` debe consumir los audios almacenados en MinIO referenciados por la clave del intento. | Should | Config MinIO (`docker-compose.yml:127-129`) |
| **RF-AN-001** | El `analytics-service` debe consolidar métricas de progreso terapéutico por paciente y por plan. | Should | Esquema `analytics`, estado *esqueleto* |
| **RF-ML-001** | El `mlops-service` debe gestionar el ciclo de vida de los modelos de evaluación y el etiquetado fonémico de datos mediante Label Studio. | Should | `docker-compose.yml:166-185`, esquema `mlops` |

---

## 4. Requerimientos No Funcionales

> Clasificados según las características de calidad del estándar **ISO/IEC 25010**.

### 4.1. Seguridad (*Security*)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RNF-SEC-001** | Las contraseñas deben almacenarse cifradas con bcrypt (función de derivación con sal), nunca en texto plano. | Must | `auth.py:6-10` |
| **RNF-SEC-002** | La autenticación entre cliente y servicios debe basarse en *tokens* JWT firmados con HS256. | Must | `auth.py:12-25`, `config.py:7` |
| **RNF-SEC-003** | Los *tokens* de acceso deben tener una vida útil corta (15 minutos) para acotar la ventana de exposición ante robo de credenciales. | Must | `config.py:8` |
| **RNF-SEC-004** | Los *tokens* de refresco deben expirar a los 7 días y ser de un solo uso, con rotación en cada renovación. | Must | `config.py:9`, `main.py:111-124` |
| **RNF-SEC-005** | Los *tokens* de refresco deben persistirse únicamente como *hash* (SHA-256), de modo que un compromiso de la base de datos no exponga *tokens* utilizables. | Must | `main.py:86` |
| **RNF-SEC-006** | Cada servicio debe validar el JWT de forma autónoma, sin depender de un servicio central de autenticación en el camino crítico de cada petición. | Must | `clinical-service/main.py:34-42` |
| **RNF-SEC-007** | El sistema debe aplicar el principio de **mínimo privilegio** en la base de datos: cada servicio accede exclusivamente a su propio esquema mediante un usuario dedicado. | Must | `infra/postgres/init.sql:15-29` |
| **RNF-SEC-008** | Los datos clínicos deben poder disociarse de la identidad del paciente mediante seudonimización, en línea con buenas prácticas de protección de datos sensibles de salud. | Should | `models.py:17` (`pseudonym_id`) |
| **RNF-SEC-009** | La clave secreta de firma y las credenciales no deben estar embebidas en el código productivo; deben inyectarse por variables de entorno. *(Deuda técnica: el valor por defecto de desarrollo debe reemplazarse en producción.)* | Must | `config.py:6` |

### 4.2. Mantenibilidad (*Maintainability*)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RNF-MNT-001** | El sistema debe estar organizado en microservicios de responsabilidad única, con una estructura interna homogénea (`config`, `database`, `models`, `schemas`, `main`, `events`). | Must | Estructura `services/<name>/app/` |
| **RNF-MNT-002** | Los contratos de entrada/salida deben validarse mediante esquemas Pydantic tipados, desacoplados de los modelos de persistencia. | Must | `schemas.py` (ambos servicios) |
| **RNF-MNT-003** | La configuración debe centralizarse en un objeto de *settings* tipado que lea variables de entorno. | Should | `config.py` (pydantic-settings) |
| **RNF-MNT-004** | El sistema debe exponer documentación de la API autogenerada e interactiva (OpenAPI / Swagger UI) para cada servicio. | Should | FastAPI `root_path`, `ReadMe.MD:56-59` |
| **RNF-MNT-005** | El agregado de un nuevo microservicio no debe requerir cambios en los servicios existentes, apoyándose en esquemas de base de datos preaprovisionados. | Should | `init.sql:1-6`, `CLAUDE.md` (guía de extensión) |

### 4.3. Portabilidad y Despliegue (*Portability*)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RNF-POR-001** | El sistema completo debe poder desplegarse de forma reproducible mediante contenedores Docker orquestados con Docker Compose. | Must | `docker-compose.yml` |
| **RNF-POR-002** | Los microservicios deben poder activarse selectivamente mediante *profiles* de Docker Compose, sin requerir levantar todo el sistema. | Should | `docker-compose.yml:98-99` (`profiles: services`) |
| **RNF-POR-003** | Toda la parametrización sensible al entorno (URLs de base de datos, Redis, MinIO, credenciales) debe inyectarse por variables de entorno. | Must | `docker-compose.yml:84-93` y análogos |
| **RNF-POR-004** | Debe ser posible ejecutar un servicio localmente (fuera de Docker) contra la infraestructura contenerizada para agilizar el desarrollo. | Could | `ReadMe.MD:69-80` |

### 4.4. Fiabilidad y Disponibilidad (*Reliability*)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RNF-REL-001** | Cada servicio debe exponer un *endpoint* `/health` que permita a orquestadores y al gateway verificar su disponibilidad. | Must | `main.py` de cada servicio |
| **RNF-REL-002** | Los servicios dependientes deben esperar a que la infraestructura crítica (PostgreSQL, Redis, MinIO) esté *healthy* antes de arrancar. | Must | `docker-compose.yml` (`depends_on: condition: service_healthy`) |
| **RNF-REL-003** | La infraestructura base debe declarar *health checks* con reintentos para detectar y recuperar fallos transitorios. | Should | `docker-compose.yml:31-35,44-48,62-66` |
| **RNF-REL-004** | El consumidor de eventos debe tolerar fallos en el procesamiento de un mensaje individual sin interrumpir el consumo de los siguientes (aislamiento de errores + *rollback* transaccional). | Must | `events.py:50-54` |
| **RNF-REL-005** | Las operaciones de escritura que involucran múltiples entidades deben ejecutarse de forma transaccional, revirtiendo los cambios ante un error parcial. | Must | `events.py:35-52` (`flush`/`commit`/`rollback`) |

### 4.5. Rendimiento y Eficiencia (*Performance Efficiency*)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RNF-PER-001** | Las columnas de búsqueda frecuente (correo, claves foráneas, códigos de invitación, pseudónimos) deben estar indexadas. | Should | `models.py` (`index=True` en ambos servicios) |
| **RNF-PER-002** | La comunicación entre servicios debe ser asíncrona y no bloqueante para evitar acoplamiento temporal, empleando un bus de eventos en memoria (Redis). | Must | `events.py`, `main.py:26-30` (identity) |
| **RNF-PER-003** | El almacenamiento de objetos de gran tamaño (audios, artefactos) debe delegarse a un *object storage* (MinIO), manteniendo en la base relacional únicamente las referencias (claves). | Must | `models.py:106` (`audio_key`), `docker-compose.yml:50-66` |

### 4.6. Compatibilidad e Interoperabilidad (*Compatibility*)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RNF-COM-001** | El sistema debe exponer una única puerta de enlace (API Gateway) que enrute las peticiones al servicio correspondiente por prefijo de ruta. | Must | Traefik, `docker-compose.yml:3-16` |
| **RNF-COM-002** | Cada servicio debe declarar su propia regla de enrutamiento de forma autónoma (descubrimiento por *labels* de Docker). | Should | `docker-compose.yml:94-97` |
| **RNF-COM-003** | El almacenamiento de objetos debe ser compatible con la API S3 para facilitar la portabilidad hacia proveedores de nube. | Could | MinIO (`docker-compose.yml:50-53`) |
| **RNF-COM-004** | Los identificadores de entidades deben ser UUID para evitar colisiones entre servicios y facilitar la integración distribuida. | Must | `models.py` (UUID como PK en todas las entidades) |

### 4.7. Escalabilidad (*derivado de la arquitectura*)

| ID | Requerimiento | Prioridad | Origen |
|----|---------------|-----------|--------|
| **RNF-ESC-001** | Los servicios deben ser *stateless* respecto de la sesión de usuario (autenticación por *token* autocontenido), habilitando el escalado horizontal por réplicas. | Should | Autenticación JWT sin sesión de servidor |
| **RNF-ESC-002** | El aislamiento por esquema y usuario de base de datos debe permitir la evolución independiente de cada dominio y su eventual migración a instancias separadas. | Could | `init.sql` |

---

## 5. Matriz de trazabilidad (resumen)

| Componente | RF cubiertos | RNF principales | Estado |
|------------|--------------|-----------------|--------|
| `identity-service` | RF-ID-001 … RF-ID-018 | SEC-001..006, SEC-009 | Implementado |
| `clinical-service` | RF-CL-001 … RF-CL-018 | SEC-007, SEC-008, REL-004/005 | Implementado |
| Bus de eventos (Redis) | RF-EV-001 … RF-EV-006 | PER-002, REL-004 | Implementado |
| API Gateway (Traefik) | — | COM-001, COM-002 | Implementado |
| Persistencia (PostgreSQL) | — | SEC-007, PER-001, ESC-002 | Implementado |
| Object storage (MinIO) | RF-SC-002 (parcial) | PER-003, COM-003 | Provisto |
| `scoring-service` | RF-SC-001, RF-SC-002 | — | Pendiente |
| `analytics-service` | RF-AN-001 | — | Pendiente |
| `mlops-service` | RF-ML-001 | — | Pendiente |

---

## 6. Deuda técnica y riesgos identificados

Sección incluida por completitud metodológica; documenta observaciones surgidas del
análisis del código que impactan requerimientos no funcionales.

| # | Observación | RNF afectado | Recomendación |
|---|-------------|--------------|---------------|
| 1 | La clave secreta JWT y las credenciales figuran como valores por defecto en el código/compose. | RNF-SEC-009 | Externalizar a un gestor de secretos; eliminar *defaults* en producción. |
| 2 | El bus Redis Pub/Sub no garantiza la entrega: un evento emitido mientras el consumidor está caído se pierde. | RF-EV-001, RNF-REL-004 | Evaluar Redis Streams o un *broker* con persistencia (RabbitMQ/Kafka) y *outbox pattern*. |
| 3 | Lógica común (validación JWT, `config`, `database`) duplicada por copia en cada servicio. | RNF-MNT-001 | Extraer una librería compartida (*core*) versionada. |
| 4 | El esquema se crea con `create_all()`; Alembic está declarado pero inactivo. | RNF-MNT-005 | Adoptar migraciones versionadas para cambios de esquema controlados. |
| 5 | La autorización es incompleta: se valida la autenticidad del *token* pero no se verifica el rol en la mayoría de los *endpoints*. | RNF-SEC-006 | Incorporar control de acceso basado en roles (RBAC) en los *endpoints* sensibles. |

---

*Documento generado a partir del análisis estático del repositorio `Fonia_Back`
(rama `main`). La columna «Origen» referencia archivos y líneas del código fuente al
momento del análisis y debe actualizarse ante cambios en la base de código.*
