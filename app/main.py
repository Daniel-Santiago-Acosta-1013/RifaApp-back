import os

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from mangum import Mangum

from app.api.routes import auth, health, migrations, purchases, raffles_v2
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

API_PREFIX = "/rifaapp"
api_gateway_base_path = os.getenv("API_GATEWAY_BASE_PATH", "").strip()
if api_gateway_base_path and not api_gateway_base_path.startswith("/"):
    api_gateway_base_path = f"/{api_gateway_base_path}"

app = FastAPI(
    title="RifaApp API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=f"{API_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(migrations.router)
api_router.include_router(raffles_v2.router)
api_router.include_router(purchases.router)
app.include_router(api_router)


@app.get(f"{API_PREFIX}/docs", include_in_schema=False)
def swagger_ui(request: Request):
    root_path = request.scope.get("root_path", "").rstrip("/")
    openapi_url = f"{root_path}{app.openapi_url}"
    return get_swagger_ui_html(openapi_url=openapi_url, title=f"{app.title} - Swagger UI")


@app.get(f"{API_PREFIX}/redoc", include_in_schema=False)
def redoc(request: Request):
    root_path = request.scope.get("root_path", "").rstrip("/")
    openapi_url = f"{root_path}{app.openapi_url}"
    return get_redoc_html(openapi_url=openapi_url, title=f"{app.title} - ReDoc")

handler = Mangum(app, api_gateway_base_path=api_gateway_base_path or None)
