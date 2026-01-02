from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.schemas import HealthResponse

router = APIRouter(tags=["meta"])


@router.get("/")
def root():
    return {"ok": True, "service": "RifaApp API"}


@router.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc)}


@router.get("/version")
def version():
    return {"version": "1.0.0"}
