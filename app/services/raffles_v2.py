from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
from typing import Optional

from fastapi import HTTPException

from app.db.connection import fetch_all, fetch_one, run_transaction
from app.models.schemas import PurchaseConfirmRequest, RaffleCreateV2, ReservationRequest
from app.services.participants import get_or_create_participant

MAX_RESERVATION_MINUTES = 30


def _normalize_status(status: Optional[str]) -> str:
    if not status:
        return "open"
    normalized = status.lower().strip()
    if normalized == "published":
        return "open"
    return normalized


def _raffle_row(row: dict) -> dict:
    number_start = row.get("number_start") or 1
    total_tickets = row["total_tickets"]
    number_end = number_start + total_tickets - 1
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "description": row.get("description"),
        "ticket_price": row["ticket_price"],
        "currency": row["currency"],
        "total_tickets": total_tickets,
        "tickets_sold": row.get("tickets_sold", 0) or 0,
        "tickets_reserved": row.get("tickets_reserved", 0) or 0,
        "status": row["status"],
        "draw_at": row.get("draw_at"),
        "winner_ticket_id": str(row["winner_ticket_id"]) if row.get("winner_ticket_id") else None,
        "number_start": number_start,
        "number_end": number_end,
        "number_padding": row.get("number_padding"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_raffle(payload: RaffleCreateV2) -> dict:
    raffle_id = uuid.uuid4()
    status = _normalize_status(payload.status)
    if status not in ("open", "draft", "closed", "cancelled", "drawn"):
        raise HTTPException(status_code=400, detail="Invalid raffle status")
    row = fetch_one(
        """
        INSERT INTO raffles (
            id, title, description, ticket_price, currency, total_tickets,
            status, draw_at, number_start, number_padding
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, title, description, ticket_price, currency, total_tickets, status,
                  draw_at, winner_ticket_id, number_start, number_padding, created_at, updated_at
        """,
        (
            raffle_id,
            payload.title,
            payload.description,
            payload.ticket_price,
            payload.currency.upper(),
            payload.total_tickets,
            status,
            payload.draw_at,
            payload.number_start,
            payload.number_padding,
        ),
    )
    return _raffle_row({**row, "tickets_sold": 0, "tickets_reserved": 0})


def list_raffles(status: Optional[str] = None) -> list[dict]:
    sql = """
        SELECT r.id, r.title, r.description, r.ticket_price, r.currency, r.total_tickets,
               r.status, r.draw_at, r.winner_ticket_id, r.number_start, r.number_padding,
               r.created_at, r.updated_at,
               COALESCE(s.sold, 0) AS tickets_sold,
               COALESCE(res.reserved, 0) AS tickets_reserved
        FROM raffles r
        LEFT JOIN (
            SELECT raffle_id, COUNT(*) AS sold
            FROM tickets
            WHERE status IN ('paid', 'sold')
            GROUP BY raffle_id
        ) s ON s.raffle_id = r.id
        LEFT JOIN (
            SELECT raffle_id, COUNT(*) AS reserved
            FROM tickets
            WHERE status = 'reserved' AND reserved_until > now()
            GROUP BY raffle_id
        ) res ON res.raffle_id = r.id
    """
    params: tuple = ()
    if status:
        sql += " WHERE r.status = %s"
        params = (status,)
    sql += " ORDER BY r.created_at DESC"
    rows = fetch_all(sql, params)
    return [_raffle_row(row) for row in rows]


def get_raffle(raffle_id: uuid.UUID) -> dict:
    row = fetch_one(
        """
        SELECT r.id, r.title, r.description, r.ticket_price, r.currency, r.total_tickets,
               r.status, r.draw_at, r.winner_ticket_id, r.number_start, r.number_padding,
               r.created_at, r.updated_at,
               COALESCE(s.sold, 0) AS tickets_sold,
               COALESCE(res.reserved, 0) AS tickets_reserved
        FROM raffles r
        LEFT JOIN (
            SELECT raffle_id, COUNT(*) AS sold
            FROM tickets
            WHERE status IN ('paid', 'sold')
            GROUP BY raffle_id
        ) s ON s.raffle_id = r.id
        LEFT JOIN (
            SELECT raffle_id, COUNT(*) AS reserved
            FROM tickets
            WHERE status = 'reserved' AND reserved_until > now()
            GROUP BY raffle_id
        ) res ON res.raffle_id = r.id
        WHERE r.id = %s
        """,
        (raffle_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Raffle not found")
    return _raffle_row(row)


def list_numbers(
    raffle_id: uuid.UUID, offset: int = 0, limit: Optional[int] = None
) -> dict:
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be >= 0")
    raffle = fetch_one(
        """
        SELECT id, total_tickets, number_start, number_padding, status
        FROM raffles
        WHERE id = %s
        """,
        (raffle_id,),
    )
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")
    total_tickets = raffle["total_tickets"]
    number_start = raffle.get("number_start") or 1
    number_end = number_start + total_tickets - 1
    total_numbers = total_tickets
    if limit is None:
        limit = total_numbers
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be positive")
    start_number = number_start + offset
    if start_number > number_end:
        return {
            "raffle_id": str(raffle_id),
            "number_start": number_start,
            "number_end": number_end,
            "number_padding": raffle.get("number_padding"),
            "total_numbers": total_numbers,
            "offset": offset,
            "limit": limit,
            "counts": {"available": total_numbers, "reserved": 0, "sold": 0},
            "numbers": [],
        }
    end_number = min(number_end, start_number + limit - 1)
    rows = fetch_all(
        """
        SELECT number, status, reserved_until
        FROM tickets
        WHERE raffle_id = %s AND number BETWEEN %s AND %s
        """,
        (raffle_id, start_number, end_number),
    )
    now = datetime.now(timezone.utc)
    status_by_number: dict[int, dict] = {}
    for row in rows:
        status = row["status"]
        reserved_until = row.get("reserved_until")
        if status == "reserved" and reserved_until and reserved_until < now:
            continue
        status_by_number[row["number"]] = {
            "status": status,
            "reserved_until": reserved_until,
        }
    padding = raffle.get("number_padding")
    numbers = []
    counts = {"available": 0, "reserved": 0, "sold": 0}
    for number in range(start_number, end_number + 1):
        ticket = status_by_number.get(number)
        if not ticket:
            status = "available"
            reserved_until = None
        else:
            status = ticket["status"]
            if status in ("paid", "sold"):
                status = "sold"
            elif status != "reserved":
                status = "available"
            reserved_until = ticket.get("reserved_until")
        counts[status] = counts.get(status, 0) + 1
        label = str(number).zfill(padding) if padding else str(number)
        numbers.append(
            {
                "number": number,
                "label": label,
                "status": status,
                "reserved_until": reserved_until,
            }
        )
    return {
        "raffle_id": str(raffle_id),
        "number_start": number_start,
        "number_end": number_end,
        "number_padding": padding,
        "total_numbers": total_numbers,
        "offset": offset,
        "limit": limit,
        "counts": counts,
        "numbers": numbers,
    }


def reserve_numbers(raffle_id: uuid.UUID, payload: ReservationRequest) -> dict:
    numbers = payload.numbers
    if len(set(numbers)) != len(numbers):
        raise HTTPException(status_code=400, detail="Duplicate numbers are not allowed")
    ttl_minutes = min(payload.ttl_minutes, MAX_RESERVATION_MINUTES)

    def _handler(conn):
        cur = conn.cursor()
        cur.execute(
            """
            SELECT total_tickets, status, ticket_price, currency, number_start, number_padding
            FROM raffles
            WHERE id = %s
            FOR UPDATE
            """,
            (raffle_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            raise HTTPException(status_code=404, detail="Raffle not found")
        total_tickets, status, ticket_price, currency, number_start, _ = row
        if status not in ("open", "published"):
            cur.close()
            raise HTTPException(status_code=400, detail="Raffle is not open for reservations")
        number_start = number_start or 1
        number_end = number_start + total_tickets - 1
        for number in numbers:
            if number < number_start or number > number_end:
                cur.close()
                raise HTTPException(status_code=400, detail="Number out of range")
        cur.execute(
            """
            DELETE FROM tickets
            WHERE raffle_id = %s
              AND status = 'reserved'
              AND reserved_until IS NOT NULL
              AND reserved_until < now()
            """,
            (raffle_id,),
        )
        participant_id = get_or_create_participant(conn, payload.participant)
        reservation_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        conflicts: list[int] = []
        for number in numbers:
            ticket_id = uuid.uuid4()
            cur.execute(
                """
                INSERT INTO tickets (
                    id, raffle_id, participant_id, number, status,
                    reserved_at, reserved_until, reservation_id, purchased_at
                )
                VALUES (%s, %s, %s, %s, 'reserved', now(), %s, %s, NULL)
                ON CONFLICT DO NOTHING
                """,
                (ticket_id, raffle_id, participant_id, number, expires_at, reservation_id),
            )
            if cur.rowcount != 1:
                conflicts.append(number)
        if conflicts:
            cur.close()
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Some numbers are no longer available",
                    "numbers": conflicts,
                },
            )
        cur.close()
        total_price = Decimal(ticket_price) * len(numbers)
        return {
            "reservation_id": str(reservation_id),
            "participant_id": str(participant_id),
            "raffle_id": str(raffle_id),
            "numbers": sorted(numbers),
            "expires_at": expires_at,
            "ticket_price": ticket_price,
            "currency": currency,
            "total_price": total_price,
        }

    return run_transaction(_handler)


def confirm_purchase(raffle_id: uuid.UUID, payload: PurchaseConfirmRequest) -> dict:
    def _handler(conn):
        cur = conn.cursor()
        cur.execute(
            """
            SELECT total_tickets, status, ticket_price, currency
            FROM raffles
            WHERE id = %s
            FOR UPDATE
            """,
            (raffle_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            raise HTTPException(status_code=404, detail="Raffle not found")
        total_tickets, status, ticket_price, currency = row
        if status not in ("open", "published"):
            cur.close()
            raise HTTPException(status_code=400, detail="Raffle is not open for purchases")
        participant_id: Optional[uuid.UUID] = None
        if payload.participant_id:
            try:
                participant_id = uuid.UUID(payload.participant_id)
            except ValueError as exc:
                cur.close()
                raise HTTPException(status_code=400, detail="Invalid participant_id") from exc
        elif payload.participant:
            participant_id = get_or_create_participant(conn, payload.participant)
        else:
            cur.close()
            raise HTTPException(status_code=400, detail="Participant is required")
        cur.execute(
            """
            SELECT id, number
            FROM tickets
            WHERE raffle_id = %s
              AND status = 'reserved'
              AND reservation_id = %s
              AND participant_id = %s
              AND reserved_until > now()
            FOR UPDATE
            """,
            (raffle_id, payload.reservation_id, participant_id),
        )
        rows = cur.fetchall()
        if not rows:
            cur.close()
            raise HTTPException(status_code=400, detail="Reservation expired or not found")
        ticket_ids = [row[0] for row in rows]
        numbers = [row[1] for row in rows]
        purchase_id = uuid.uuid4()
        total_price = Decimal(ticket_price) * len(ticket_ids)
        cur.execute(
            """
            INSERT INTO purchases (
                id, raffle_id, participant_id, status, total_price, currency, payment_method
            ) VALUES (%s, %s, %s, 'confirmed', %s, %s, %s)
            """,
            (purchase_id, raffle_id, participant_id, total_price, currency, payload.payment_method),
        )
        placeholders = ", ".join(["%s"] * len(ticket_ids))
        cur.execute(
            f"""
            UPDATE tickets
            SET status = 'sold',
                purchased_at = now(),
                reserved_until = NULL,
                reservation_id = NULL,
                purchase_id = %s
            WHERE id IN ({placeholders})
            """,
            [purchase_id, *ticket_ids],
        )
        cur.execute(
            "SELECT COUNT(*) FROM tickets WHERE raffle_id = %s AND status IN ('paid', 'sold')",
            (raffle_id,),
        )
        sold_count = cur.fetchone()[0]
        if sold_count >= total_tickets:
            cur.execute(
                "UPDATE raffles SET status = 'closed', updated_at = now() WHERE id = %s",
                (raffle_id,),
            )
        cur.execute("SELECT created_at FROM purchases WHERE id = %s", (purchase_id,))
        created_at = cur.fetchone()[0]
        cur.close()
        return {
            "purchase_id": str(purchase_id),
            "raffle_id": str(raffle_id),
            "participant_id": str(participant_id),
            "numbers": sorted(numbers),
            "total_price": total_price,
            "currency": currency,
            "status": "confirmed",
            "created_at": created_at,
        }

    return run_transaction(_handler)


def release_reservation(raffle_id: uuid.UUID, reservation_id: str) -> dict:
    def _handler(conn):
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM tickets
            WHERE raffle_id = %s AND reservation_id = %s AND status = 'reserved'
            """,
            (raffle_id, reservation_id),
        )
        released = cur.rowcount
        cur.close()
        return {"status": "released", "released": released}

    return run_transaction(_handler)
