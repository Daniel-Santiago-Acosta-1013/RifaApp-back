from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
from typing import Optional

from fastapi import HTTPException

from app.cqrs.commands.participants import get_or_create_participant
from app.db.connection import run_transaction
from app.models.schemas import PurchaseConfirmRequest, RaffleCreateV2, RaffleUpdateV2, ReservationRequest

MAX_RESERVATION_MINUTES = 30


def _normalize_status(status: Optional[str]) -> str:
    if not status:
        return "open"
    normalized = status.lower().strip()
    if normalized == "published":
        return "open"
    return normalized


def _raffle_out_from_row(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "description": row.get("description"),
        "ticket_price": row["ticket_price"],
        "currency": row["currency"],
        "total_tickets": row["total_tickets"],
        "tickets_sold": row.get("tickets_sold", 0) or 0,
        "tickets_reserved": row.get("tickets_reserved", 0) or 0,
        "status": row["status"],
        "draw_at": row.get("draw_at"),
        "winner_ticket_id": str(row["winner_ticket_id"]) if row.get("winner_ticket_id") else None,
        "number_start": row["number_start"],
        "number_end": row["number_end"],
        "number_padding": row.get("number_padding"),
        "owner_id": str(row["owner_id"]) if row.get("owner_id") else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _seed_raffle_numbers(
    cur,
    raffle_id: uuid.UUID,
    number_start: int,
    number_end: int,
    number_padding: Optional[int],
) -> None:
    cur.execute(
        """
        INSERT INTO raffle_numbers_read (
            raffle_id, number, status, reserved_until, reservation_id,
            purchase_id, participant_id, label, updated_at
        )
        SELECT %s,
               n,
               'available',
               NULL,
               NULL,
               NULL,
               NULL,
               CASE WHEN %s::int IS NULL THEN n::text ELSE lpad(n::text, %s::int, '0') END,
               now()
        FROM generate_series(%s::int, %s::int) AS n
        """,
        (raffle_id, number_padding, number_padding, number_start, number_end),
    )


def create_raffle(payload: RaffleCreateV2) -> dict:
    def _handler(conn):
        cur = conn.cursor()
        status = _normalize_status(payload.status)
        if status not in ("open", "draft", "closed", "cancelled", "drawn"):
            cur.close()
            raise HTTPException(status_code=400, detail="Invalid raffle status")
        raffle_id = uuid.uuid4()
        cur.execute(
            """
            INSERT INTO raffles (
                id, title, description, ticket_price, currency, total_tickets,
                status, draw_at, number_start, number_padding, owner_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, title, description, ticket_price, currency, total_tickets,
                      status, draw_at, winner_ticket_id, number_start, number_padding,
                      owner_id, created_at, updated_at
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
                payload.owner_id,
            ),
        )
        row = cur.fetchone()
        number_start = 1 if row[9] is None else row[9]
        total_tickets = row[5]
        number_end = number_start + total_tickets - 1
        number_padding = row[10]
        cur.execute(
            """
            INSERT INTO raffles_read (
                id, title, description, ticket_price, currency, total_tickets,
                status, draw_at, winner_ticket_id, number_start, number_end,
                number_padding, owner_id, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                number_start,
                number_end,
                number_padding,
                row[11],
                row[12],
                row[13],
            ),
        )
        _seed_raffle_numbers(cur, raffle_id, number_start, number_end, number_padding)
        cur.close()
        return {
            "id": str(row[0]),
            "title": row[1],
            "description": row[2],
            "ticket_price": row[3],
            "currency": row[4],
            "total_tickets": row[5],
            "tickets_sold": 0,
            "tickets_reserved": 0,
            "status": row[6],
            "draw_at": row[7],
            "winner_ticket_id": str(row[8]) if row[8] else None,
            "number_start": number_start,
            "number_end": number_end,
            "number_padding": number_padding,
            "owner_id": str(row[11]) if row[11] else None,
            "created_at": row[12],
            "updated_at": row[13],
        }

    return run_transaction(_handler)


def update_raffle(raffle_id: uuid.UUID, payload: RaffleUpdateV2, actor_id: Optional[str]) -> dict:
    if not actor_id:
        raise HTTPException(status_code=401, detail="Missing user id")
    try:
        editor_id = uuid.UUID(actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    data = payload.dict(exclude_unset=True)
    if "status" in data:
        data["status"] = _normalize_status(data["status"])
        if data["status"] not in ("open", "draft", "closed", "cancelled", "drawn"):
            raise HTTPException(status_code=400, detail="Invalid raffle status")
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    def _handler(conn):
        cur = conn.cursor()
        cur.execute("SELECT owner_id FROM raffles WHERE id = %s FOR UPDATE", (raffle_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            raise HTTPException(status_code=404, detail="Raffle not found")
        owner_id = row[0]
        if owner_id is None or owner_id != editor_id:
            cur.close()
            raise HTTPException(status_code=403, detail="Not allowed to edit this raffle")

        set_clauses = []
        params: list = []
        for field in ("title", "description", "draw_at", "status"):
            if field in data:
                set_clauses.append(f"{field} = %s")
                params.append(data[field])
        set_clauses.append("updated_at = now()")
        params.append(raffle_id)
        set_clause = ", ".join(set_clauses)
        cur.execute(f"UPDATE raffles SET {set_clause} WHERE id = %s", params)
        cur.execute(f"UPDATE raffles_read SET {set_clause} WHERE id = %s", params)

        cur.execute(
            """
            SELECT r.id, r.title, r.description, r.ticket_price, r.currency, r.total_tickets,
                   r.status, r.draw_at, r.winner_ticket_id, r.number_start, r.number_end,
                   r.number_padding, r.owner_id, r.created_at, r.updated_at,
                   COALESCE(s.sold, 0) AS tickets_sold,
                   COALESCE(res.reserved, 0) AS tickets_reserved
            FROM raffles_read r
            LEFT JOIN (
                SELECT raffle_id, COUNT(*) AS sold
                FROM raffle_numbers_read
                WHERE status = 'sold'
                GROUP BY raffle_id
            ) s ON s.raffle_id = r.id
            LEFT JOIN (
                SELECT raffle_id, COUNT(*) AS reserved
                FROM raffle_numbers_read
                WHERE status = 'reserved' AND reserved_until > now()
                GROUP BY raffle_id
            ) res ON res.raffle_id = r.id
            WHERE r.id = %s
            """,
            (raffle_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            raise HTTPException(status_code=404, detail="Raffle not found")
        columns = [col[0] for col in cur.description]
        cur.close()
        return _raffle_out_from_row(dict(zip(columns, row)))

    return run_transaction(_handler)


def delete_raffle(raffle_id: uuid.UUID, actor_id: Optional[str]) -> dict:
    if not actor_id:
        raise HTTPException(status_code=401, detail="Missing user id")
    try:
        editor_id = uuid.UUID(actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    def _handler(conn):
        cur = conn.cursor()
        cur.execute("SELECT owner_id FROM raffles WHERE id = %s FOR UPDATE", (raffle_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            raise HTTPException(status_code=404, detail="Raffle not found")
        owner_id = row[0]
        if owner_id is None or owner_id != editor_id:
            cur.close()
            raise HTTPException(status_code=403, detail="Not allowed to delete this raffle")

        cur.execute("DELETE FROM purchases_read WHERE raffle_id = %s", (raffle_id,))
        cur.execute("DELETE FROM raffle_numbers_read WHERE raffle_id = %s", (raffle_id,))
        cur.execute("DELETE FROM raffles_read WHERE id = %s", (raffle_id,))
        cur.execute("DELETE FROM raffles WHERE id = %s", (raffle_id,))
        cur.close()
        return {"status": "deleted", "raffle_id": str(raffle_id)}

    return run_transaction(_handler)


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
        number_start = 1 if number_start is None else number_start
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
            RETURNING number
            """,
            (raffle_id,),
        )
        expired_rows = cur.fetchall()
        expired_numbers = [row[0] for row in expired_rows]
        if expired_numbers:
            placeholders = ", ".join(["%s"] * len(expired_numbers))
            cur.execute(
                f"""
                UPDATE raffle_numbers_read
                SET status = 'available',
                    reserved_until = NULL,
                    reservation_id = NULL,
                    participant_id = NULL,
                    purchase_id = NULL,
                    updated_at = now()
                WHERE raffle_id = %s AND number IN ({placeholders})
                """,
                [raffle_id, *expired_numbers],
            )

        participant_id = get_or_create_participant(conn, payload.participant)
        reservation_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        conflicts: list[int] = []
        reserved_numbers: list[int] = []
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
            else:
                reserved_numbers.append(number)

        if conflicts:
            cur.close()
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Some numbers are no longer available",
                    "numbers": conflicts,
                },
            )

        if reserved_numbers:
            placeholders = ", ".join(["%s"] * len(reserved_numbers))
            cur.execute(
                f"""
                UPDATE raffle_numbers_read
                SET status = 'reserved',
                    reserved_until = %s,
                    reservation_id = %s,
                    participant_id = %s,
                    purchase_id = NULL,
                    updated_at = now()
                WHERE raffle_id = %s AND number IN ({placeholders})
                """,
                [expires_at, reservation_id, participant_id, raffle_id, *reserved_numbers],
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
        numbers = sorted(row[1] for row in rows)
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
        cur.execute("SELECT title, status FROM raffles WHERE id = %s", (raffle_id,))
        raffle_row = cur.fetchone()
        raffle_title = raffle_row[0]
        raffle_status = raffle_row[1]

        if numbers:
            placeholders = ", ".join(["%s"] * len(numbers))
            cur.execute(
                f"""
                UPDATE raffle_numbers_read
                SET status = 'sold',
                    reserved_until = NULL,
                    reservation_id = NULL,
                    purchase_id = %s,
                    participant_id = %s,
                    updated_at = now()
                WHERE raffle_id = %s AND number IN ({placeholders})
                """,
                [purchase_id, participant_id, raffle_id, *numbers],
            )
        cur.execute(
            """
            INSERT INTO purchases_read (
                purchase_id, raffle_id, participant_id, raffle_title, raffle_status,
                numbers, total_price, currency, status, payment_method, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                purchase_id,
                raffle_id,
                participant_id,
                raffle_title,
                raffle_status,
                numbers,
                total_price,
                currency,
                "confirmed",
                payload.payment_method,
                created_at,
            ),
        )
        cur.execute(
            "UPDATE raffles_read SET status = %s, updated_at = now() WHERE id = %s",
            (raffle_status, raffle_id),
        )
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
            RETURNING number
            """,
            (raffle_id, reservation_id),
        )
        rows = cur.fetchall()
        released_numbers = [row[0] for row in rows]
        if released_numbers:
            placeholders = ", ".join(["%s"] * len(released_numbers))
            cur.execute(
                f"""
                UPDATE raffle_numbers_read
                SET status = 'available',
                    reserved_until = NULL,
                    reservation_id = NULL,
                    participant_id = NULL,
                    purchase_id = NULL,
                    updated_at = now()
                WHERE raffle_id = %s AND number IN ({placeholders})
                """,
                [raffle_id, *released_numbers],
            )
        released = len(released_numbers)
        cur.close()
        return {"status": "released", "released": released}

    return run_transaction(_handler)


def draw_raffle(raffle_id: uuid.UUID) -> dict:
    def _handler(conn):
        cur = conn.cursor()
        cur.execute(
            "SELECT status, winner_ticket_id FROM raffles WHERE id = %s FOR UPDATE",
            (raffle_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            raise HTTPException(status_code=404, detail="Raffle not found")
        status, winner_ticket_id = row
        if status == "drawn" and winner_ticket_id:
            cur.execute(
                "SELECT id, participant_id, number FROM tickets WHERE id = %s",
                (winner_ticket_id,),
            )
            ticket = cur.fetchone()
            if ticket:
                cur.execute(
                    "UPDATE raffles_read SET status = 'drawn', winner_ticket_id = %s, updated_at = now() WHERE id = %s",
                    (winner_ticket_id, raffle_id),
                )
                cur.close()
                return {
                    "raffle_id": str(raffle_id),
                    "winner_ticket_id": str(ticket[0]),
                    "winner_participant_id": str(ticket[1]),
                    "winning_number": ticket[2],
                }
            cur.close()
            raise HTTPException(status_code=404, detail="Winning ticket not found")

        cur.execute(
            """
            SELECT id, participant_id, number
            FROM tickets
            WHERE raffle_id = %s AND status IN ('paid', 'sold')
            ORDER BY random()
            LIMIT 1
            """,
            (raffle_id,),
        )
        ticket = cur.fetchone()
        if not ticket:
            cur.close()
            raise HTTPException(status_code=400, detail="No tickets sold")
        ticket_id, participant_id, number = ticket
        cur.execute(
            "UPDATE raffles SET status = 'drawn', winner_ticket_id = %s, updated_at = now() WHERE id = %s",
            (ticket_id, raffle_id),
        )
        cur.execute(
            "UPDATE raffles_read SET status = 'drawn', winner_ticket_id = %s, updated_at = now() WHERE id = %s",
            (ticket_id, raffle_id),
        )
        cur.close()
        return {
            "raffle_id": str(raffle_id),
            "winner_ticket_id": str(ticket_id),
            "winner_participant_id": str(participant_id),
            "winning_number": number,
        }

    return run_transaction(_handler)
