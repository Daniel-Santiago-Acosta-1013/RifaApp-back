import uuid

from fastapi import APIRouter

from app.api.dependencies import require_db
from app.models.schemas import PurchaseOut
from app.services import purchases

router = APIRouter(prefix="/v2/participants", tags=["purchases"])


@router.get("/{participant_id}/purchases", response_model=list[PurchaseOut])
def list_purchases(participant_id: uuid.UUID):
    require_db()
    return purchases.list_purchases(participant_id)
