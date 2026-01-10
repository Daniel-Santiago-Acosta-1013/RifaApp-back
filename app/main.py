import os
import traceback

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse
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


@app.exception_handler(HTTPException)
def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": "http_error"},
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Validation error", "type": "validation_error"},
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(_: Request, exc: Exception):
    if settings.expose_errors:
        detail = {
            "type": exc.__class__.__name__,
            "message": str(exc) or "Unhandled error",
            "trace": traceback.format_exc(),
        }
    else:
        detail = "Internal Server Error"
    return JSONResponse(status_code=500, content={"detail": detail, "type": "server_error"})


def _docs_base_path(request: Request) -> str:
    root_path = request.scope.get("root_path", "").rstrip("/")
    if root_path:
        return root_path
    if api_gateway_base_path:
        return api_gateway_base_path.rstrip("/")
    path = request.url.path.rstrip("/")
    suffix = f"{API_PREFIX}/docs"
    if path.endswith(suffix):
        return path[: -len(suffix)]
    return ""


@app.get(f"{API_PREFIX}/docs", include_in_schema=False)
def swagger_ui(request: Request):
    base_path = _docs_base_path(request)
    openapi_url = f"{base_path}{app.openapi_url}" if base_path else app.openapi_url
    return get_swagger_ui_html(openapi_url=openapi_url, title=f"{app.title} - Swagger UI")


@app.get(f"{API_PREFIX}/redoc", include_in_schema=False)
def redoc(request: Request):
    base_path = _docs_base_path(request)
    openapi_url = f"{base_path}{app.openapi_url}" if base_path else app.openapi_url
    return get_redoc_html(openapi_url=openapi_url, title=f"{app.title} - ReDoc")

handler = Mangum(app, api_gateway_base_path=api_gateway_base_path or None)
