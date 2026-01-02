import os

from fastapi import APIRouter, FastAPI
from mangum import Mangum

from app.api.routes import health, raffles, tickets
from app.core.logging import configure_logging

configure_logging()

API_PREFIX = "/rifaapp"
api_gateway_base_path = os.getenv("API_GATEWAY_BASE_PATH", "").strip()
if api_gateway_base_path and not api_gateway_base_path.startswith("/"):
    api_gateway_base_path = f"/{api_gateway_base_path}"

app = FastAPI(
    title="RifaApp API",
    version="1.0.0",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(health.router)
api_router.include_router(raffles.router)
api_router.include_router(tickets.router)
app.include_router(api_router)

handler = Mangum(app, api_gateway_base_path=api_gateway_base_path or None)
