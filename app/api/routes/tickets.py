import uuid

from fastapi import APIRouter

from app.api.dependencies import require_db
from app.models.schemas import TicketOut, TicketPurchaseRequest, TicketPurchaseResponse
from app.services import tickets

router = APIRouter(prefix="/raffles/{raffle_id}/tickets", tags=["tickets"])


@router.get("", response_model=list[TicketOut])
def list_tickets(raffle_id: uuid.UUID):
    require_db()
    return tickets.list_tickets(raffle_id)


@router.post("", response_model=TicketPurchaseResponse, status_code=201)
def purchase_tickets(raffle_id: uuid.UUID, payload: TicketPurchaseRequest):
    require_db()
    return tickets.purchase_tickets(raffle_id, payload)
