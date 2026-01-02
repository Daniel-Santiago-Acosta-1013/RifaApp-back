# RifaApp backend (FastAPI)

API de rifas para ejecutarse en AWS Lambda con FastAPI + Mangum.

## Requisitos
- Python 3.11
- Poetry

## Instalacion local
```
poetry install
```

## Ejecutar localmente
```
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger: `http://localhost:8000/docs`
OpenAPI: `http://localhost:8000/openapi.json`

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

## Build para Lambda
Genera `lambda_dist/` con las dependencias y el paquete `app/`:

```
./scripts/build_lambda.sh
```

Terraform en `../RifaApp-infra/` empaqueta `lambda_dist/` en `lambda.zip`.

## Deploy local con Poetry
Este comando construye la Lambda y ejecuta Terraform desde el repo infra:

```
poetry install
poetry run deploy
```

Variables requeridas:
- `AWS_PROFILE` y `AWS_REGION` (o credenciales AWS por env)
- `TF_VAR_db_password` o `DB_PASSWORD`

Opciones utiles:
- `poetry run deploy --plan-only`
- `poetry run deploy --lambda-only`
- `poetry run deploy --infra-dir /ruta/a/RifaApp-infra`

## Deploy CI/CD
Este repo puede notificar al repo de infraestructura para desplegar cambios.

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
- `GET /health`
- `POST /raffles`
- `GET /raffles`
- `GET /raffles/{raffle_id}`
- `POST /raffles/{raffle_id}/tickets`
- `GET /raffles/{raffle_id}/tickets`
- `POST /raffles/{raffle_id}/draw`
