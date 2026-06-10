# PFI — Proyecto Final Integrador

Plataforma de terapia del habla basada en microservicios (FastAPI + PostgreSQL), orquestada con Docker Compose y Traefik como API gateway.

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo

## Levantar el proyecto

### 1. Infraestructura compartida (siempre primero)

```bash
docker compose up -d postgres redis minio pgadmin api-gateway
```

Esto inicia la base de datos, Redis, MinIO, pgAdmin y el gateway. Esperar a que todos los servicios pasen a estado `healthy` (se puede verificar con `docker compose ps`).

### 2. Microservicios (según lo que se necesite)

```bash
# identity-service (autenticación y usuarios)
docker compose --profile services up -d identity-service

# clinical-service (registros clínicos y sesiones de terapia)
docker compose --profile services up -d clinical-service

# Levantar todos los servicios de una vez
docker compose --profile services up -d
```

### 3. Reconstruir un servicio tras cambios de código

```bash
docker compose --profile services up -d --build identity-service
```

### 4. Bajar todo

```bash
docker compose down
```

## URLs disponibles

| Servicio | URL |
|----------|-----|
| API Gateway (Traefik) | http://localhost:80 |
| Dashboard Traefik | http://localhost:8080 |
| identity-service (directo) | http://localhost:8001 |
| clinical-service (directo) | http://localhost:8002 |
| Label Studio | http://localhost:8090 |
| pgAdmin | http://localhost:5050 |
| MinIO consola | http://localhost:9001 |

### Documentación de la API (Swagger UI)

- Via gateway: `http://localhost/api/identity/docs` y `http://localhost/api/clinical/docs`
- Directo: `http://localhost:8001/docs` y `http://localhost:8002/docs`

## Credenciales de desarrollo

| Servicio | Usuario | Contraseña |
|----------|---------|------------|
| PostgreSQL | `pfi_admin` | `pfi_password` |
| pgAdmin | `facundopeletay46@gmail.com` | `admin` |
| MinIO | `pfi_minio` | `pfi_minio_password` |

## Desarrollo local (sin Docker para el servicio)

Para iterar rápido sin reconstruir la imagen, se puede correr un servicio directamente contra la infra Docker:

```bash
cd services/identity-service
pip install -r requirements.txt

DATABASE_URL="postgresql://identity_user:identity_pass@localhost:5432/pfi" \
REDIS_URL="redis://localhost:6379/0" \
uvicorn app.main:app --reload --port 8001
```

## Estado de los servicios

| Servicio | Estado |
|----------|--------|
| identity-service | Completo |
| clinical-service | Completo |
| scoring-service | Esqueleto |
| analytics-service | Esqueleto |
| mlops-service | Esqueleto |
