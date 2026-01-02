import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.api.dependencies import require_db
from app.models.schemas import DrawResponse, RaffleCreate, RaffleOut
from app.services import raffles

router = APIRouter(prefix="/raffles", tags=["raffles"])


@router.post("", response_model=RaffleOut, status_code=201)
def create_raffle(payload: RaffleCreate):
    require_db()
    return raffles.create_raffle(payload)


@router.get("", response_model=list[RaffleOut])
def list_raffles(status: Optional[str] = Query(None, description="Filter by status")):
    require_db()
    return raffles.list_raffles(status)


@router.get("/{raffle_id}", response_model=RaffleOut)
def get_raffle(raffle_id: uuid.UUID):
    require_db()
    return raffles.get_raffle(raffle_id)


@router.post("/{raffle_id}/draw", response_model=DrawResponse)
def draw_raffle(raffle_id: uuid.UUID):
    require_db()
    return raffles.draw_raffle(raffle_id)
