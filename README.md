# RifaApp backend (FastAPI)

API de rifas para ejecutarse en AWS Lambda con FastAPI + Mangum. Solo se expone la versión v2 de la API.

## Requisitos
- Python 3.11
- uv (Astral)
- Sqitch
- Terragrunt

Instalar Sqitch (macOS):
```
brew install cpanminus libpq
env PATH="/opt/homebrew/opt/libpq/bin:$PATH" cpanm --notest App::Sqitch
cpanm --local-lib=~/perl5 local::lib
eval "$(perl -I ~/perl5/lib/perl5 -Mlocal::lib)"
```

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

Para crear tablas automaticamente en desarrollo (usa `sqitch deploy`):
```
export AUTO_MIGRATE=true
```

Para ejecutar migraciones manuales en CI/CD, se expone:
```
POST /rifaapp/migrations/run
```

Sqitch toma los cambios desde `sqitch/` y requiere tener el binario disponible
en el entorno (PATH o `SQITCH_BIN`). Opcionalmente puedes definir:
- `SQITCH_TARGET`: override de la conexion (ej. `db:pg://user@host:5432/dbname`)
- `SQITCH_DIR`: directorio raiz donde viven `sqitch.conf` y `sqitch.plan`

En Lambda, provee `sqitch` via layer o runtime base si usas `AUTO_MIGRATE` o
el endpoint de migraciones.

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
- `app/cqrs/commands/`: write-side (comandos)
- `app/cqrs/queries/`: read-side (consultas)
- `app/db/`: conexion y schema
- `app/models/`: esquemas Pydantic
- `sqitch/`: migraciones (write model + read model)

## CQRS (fuerte)
- Write model: `raffles`, `tickets`, `purchases`, `participants`, `users`
- Read model: `raffles_read`, `raffle_numbers_read`, `purchases_read`
- Las proyecciones del read model se actualizan **sincrónicamente en la misma transacción** que los comandos.
- Las queries solo leen del read model.
- La migración `cqrs_read_model` crea y hace backfill del read model.

## Endpoints principales
- `GET /rifaapp/health`
- `POST /rifaapp/auth/register`
- `POST /rifaapp/auth/login`
- `POST /rifaapp/migrations/run`
- `POST /rifaapp/v2/raffles`
- `GET /rifaapp/v2/raffles`
- `GET /rifaapp/v2/raffles/{raffle_id}`
- `GET /rifaapp/v2/raffles/{raffle_id}/numbers`
- `POST /rifaapp/v2/raffles/{raffle_id}/reservations`
- `POST /rifaapp/v2/raffles/{raffle_id}/confirm`
- `POST /rifaapp/v2/raffles/{raffle_id}/release`
- `POST /rifaapp/v2/raffles/{raffle_id}/draw`
- `GET /rifaapp/v2/participants/{participant_id}/purchases`
