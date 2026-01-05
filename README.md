# RifaApp backend (FastAPI)

API de rifas para ejecutarse en AWS Lambda con FastAPI + Mangum.

## Requisitos
- Python 3.11
- uv (Astral)
- Terragrunt

## Instalacion local
```
uv sync --extra dev
```

## Ejecutar localmente
```
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger: `http://localhost:8000/rifaapp/docs`
OpenAPI: `http://localhost:8000/rifaapp/openapi.json`

## Variables de entorno
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

Para crear tablas automaticamente en desarrollo:
```
export AUTO_MIGRATE=true
```

Para ejecutar migraciones manuales en CI/CD, se expone:
```
POST /rifaapp/migrations/run
```

## Build para Lambda
Genera `lambda_dist/` con las dependencias y el paquete `app/`:

```
./scripts/build_lambda.sh
```

Terragrunt en `../RifaApp-infra/envs/dev/` empaqueta `lambda_dist/` en `lambda.zip`.

## Deploy local con uv
Este comando construye la Lambda y ejecuta Terragrunt desde `envs/dev` en el repo infra:

```
uv sync --extra dev
uv run deploy
```

Variables requeridas:
- `AWS_PROFILE` y `AWS_REGION` (o credenciales AWS por env)
- `TF_VAR_db_password` o `DB_PASSWORD`

Opciones utiles:
- `uv run deploy --plan-only`
- `uv run deploy --lambda-only`
- `uv run deploy --infra-dir /ruta/a/RifaApp-infra`

## Deploy CI/CD
Este repo puede notificar al repo de infraestructura para desplegar cambios.
Tambien incluye un workflow manual para ejecutar migraciones en infra.

Configura en GitHub (repo backend):
- `INFRA_REPO` (Variable): `owner/RifaApp-infra`
- `INFRA_DISPATCH_TOKEN` (Secret): token con permiso para disparar workflows en el repo infra

## Estructura
- `app/main.py`: instancia FastAPI y handler para Lambda
- `app/api/routes/`: endpoints
- `app/services/`: logica de negocio
- `app/db/`: conexion y schema
- `app/models/`: esquemas Pydantic

## Endpoints principales
- `GET /rifaapp/health`
- `POST /rifaapp/auth/register`
- `POST /rifaapp/auth/login`
- `POST /rifaapp/migrations/run`
- `POST /rifaapp/raffles`
- `GET /rifaapp/raffles`
- `GET /rifaapp/raffles/{raffle_id}`
- `POST /rifaapp/raffles/{raffle_id}/tickets`
- `GET /rifaapp/raffles/{raffle_id}/tickets`
- `POST /rifaapp/raffles/{raffle_id}/draw`
