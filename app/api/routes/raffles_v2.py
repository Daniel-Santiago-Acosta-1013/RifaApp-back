import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.api.dependencies import require_db
from app.models.schemas import (
    DrawResponse,
    PurchaseConfirmRequest,
    PurchaseConfirmResponse,
    RaffleCreateV2,
    RaffleNumbersResponse,
    RaffleOutV2,
    ReservationReleaseRequest,
    ReservationRequest,
    ReservationResponse,
)
from app.cqrs.commands import raffles as raffles_commands
from app.cqrs.queries import raffles as raffles_queries

router = APIRouter(prefix="/v2/raffles", tags=["raffles-v2"])


@router.post("", response_model=RaffleOutV2, status_code=201)
def create_raffle(payload: RaffleCreateV2):
    require_db()
    return raffles_commands.create_raffle(payload)


@router.get("", response_model=list[RaffleOutV2])
def list_raffles(status: Optional[str] = Query(None, description="Filter by status")):
    require_db()
    return raffles_queries.list_raffles(status)


@router.get("/{raffle_id}", response_model=RaffleOutV2)
def get_raffle(raffle_id: uuid.UUID):
    require_db()
    return raffles_queries.get_raffle(raffle_id)


@router.get("/{raffle_id}/numbers", response_model=RaffleNumbersResponse)
def list_numbers(
    raffle_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1),
):
    require_db()
    return raffles_queries.list_numbers(raffle_id, offset=offset, limit=limit)


@router.post("/{raffle_id}/reservations", response_model=ReservationResponse, status_code=201)
def reserve_numbers(raffle_id: uuid.UUID, payload: ReservationRequest):
    require_db()
    return raffles_commands.reserve_numbers(raffle_id, payload)


@router.post("/{raffle_id}/confirm", response_model=PurchaseConfirmResponse)
def confirm_purchase(raffle_id: uuid.UUID, payload: PurchaseConfirmRequest):
    require_db()
    return raffles_commands.confirm_purchase(raffle_id, payload)


@router.post("/{raffle_id}/release")
def release_reservation(raffle_id: uuid.UUID, payload: ReservationReleaseRequest):
    require_db()
    return raffles_commands.release_reservation(raffle_id, payload.reservation_id)


@router.post("/{raffle_id}/draw", response_model=DrawResponse)
def draw_raffle(raffle_id: uuid.UUID):
    require_db()
    return raffles_commands.draw_raffle(raffle_id)
