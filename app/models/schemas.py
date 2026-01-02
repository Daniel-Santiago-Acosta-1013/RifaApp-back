from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class HealthResponse(BaseModel):
    status: str
    time: datetime


class RaffleCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = Field(None, max_length=1000)
    ticket_price: Decimal = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    total_tickets: int = Field(..., gt=0, le=100000)
    draw_at: Optional[datetime] = None


class RaffleOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    ticket_price: Decimal
    currency: str
    total_tickets: int
    tickets_sold: int
    status: str
    draw_at: Optional[datetime]
    winner_ticket_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class ParticipantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: Optional[EmailStr] = None


class TicketPurchaseRequest(BaseModel):
    participant: ParticipantCreate
    quantity: int = Field(..., gt=0, le=50)


class TicketPurchaseResponse(BaseModel):
    raffle_id: str
    participant_id: str
    ticket_ids: list[str]
    numbers: list[int]
    total_price: Decimal
    currency: str


class TicketOut(BaseModel):
    id: str
    participant_id: str
    number: int
    status: str
    purchased_at: datetime


class DrawResponse(BaseModel):
    raffle_id: str
    winner_ticket_id: str
    winner_participant_id: str
    winning_number: int
