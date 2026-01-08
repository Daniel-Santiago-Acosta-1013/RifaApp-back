from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class HealthResponse(BaseModel):
    status: str
    time: datetime


class MigrationRunResponse(BaseModel):
    status: str
    applied_at: datetime


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    created_at: datetime


class ParticipantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: Optional[EmailStr] = None


class DrawResponse(BaseModel):
    raffle_id: str
    winner_ticket_id: str
    winner_participant_id: str
    winning_number: int


class RaffleCreateV2(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = Field(None, max_length=1000)
    ticket_price: Decimal = Field(..., gt=0)
    currency: str = Field("COP", min_length=3, max_length=3)
    total_tickets: int = Field(..., gt=0, le=100000)
    draw_at: Optional[datetime] = None
    number_start: int = Field(1, ge=0)
    number_padding: Optional[int] = Field(None, ge=1, le=6)
    status: Optional[str] = Field("open", max_length=20)


class RaffleOutV2(BaseModel):
    id: str
    title: str
    description: Optional[str]
    ticket_price: Decimal
    currency: str
    total_tickets: int
    tickets_sold: int
    tickets_reserved: int
    status: str
    draw_at: Optional[datetime]
    winner_ticket_id: Optional[str]
    number_start: int
    number_end: int
    number_padding: Optional[int]
    created_at: datetime
    updated_at: datetime


class RaffleNumber(BaseModel):
    number: int
    label: str
    status: str
    reserved_until: Optional[datetime] = None


class RaffleNumbersResponse(BaseModel):
    raffle_id: str
    number_start: int
    number_end: int
    number_padding: Optional[int]
    total_numbers: int
    offset: int
    limit: int
    counts: dict[str, int]
    numbers: list[RaffleNumber]


class ReservationRequest(BaseModel):
    participant: ParticipantCreate
    numbers: list[int] = Field(..., min_items=1, max_items=50)
    ttl_minutes: int = Field(10, ge=1, le=60)


class ReservationResponse(BaseModel):
    reservation_id: str
    participant_id: str
    raffle_id: str
    numbers: list[int]
    expires_at: datetime
    ticket_price: Decimal
    currency: str
    total_price: Decimal


class ReservationReleaseRequest(BaseModel):
    reservation_id: str


class PurchaseConfirmRequest(BaseModel):
    reservation_id: str
    participant_id: Optional[str] = None
    participant: Optional[ParticipantCreate] = None
    payment_method: Optional[str] = Field("demo", max_length=30)


class PurchaseOut(BaseModel):
    purchase_id: str
    raffle_id: str
    raffle_title: str
    raffle_status: str
    numbers: list[int]
    total_price: Decimal
    currency: str
    status: str
    payment_method: Optional[str]
    created_at: datetime


class PurchaseConfirmResponse(BaseModel):
    purchase_id: str
    raffle_id: str
    participant_id: str
    numbers: list[int]
    total_price: Decimal
    currency: str
    status: str
    created_at: datetime
