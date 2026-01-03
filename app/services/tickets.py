from __future__ import annotations

import uuid

from fastapi import HTTPException

from app.db.connection import fetch_all, run_transaction
from app.models.schemas import TicketPurchaseRequest
from app.services.participants import get_or_create_participant


def list_tickets(raffle_id: uuid.UUID) -> list[dict]:
    rows = fetch_all(
        """
        SELECT id, participant_id, number, status, purchased_at
        FROM tickets
        WHERE raffle_id = %s AND status IN ('paid', 'sold')
        ORDER BY number ASC
        """,
        (raffle_id,),
    )
    return [
        {
            "id": str(row["id"]),
            "participant_id": str(row["participant_id"]),
            "number": row["number"],
            "status": row["status"],
            "purchased_at": row["purchased_at"],
        }
        for row in rows
    ]


def purchase_tickets(raffle_id: uuid.UUID, payload: TicketPurchaseRequest) -> dict:
    def _handler(conn):
        cur = conn.cursor()
        cur.execute(
            "SELECT total_tickets, status, ticket_price, currency FROM raffles WHERE id = %s FOR UPDATE",
            (raffle_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            raise HTTPException(status_code=404, detail="Raffle not found")
        total_tickets, status, ticket_price, currency = row
        if status != "open":
            cur.close()
            raise HTTPException(status_code=400, detail="Raffle is not open")
        cur.execute(
            "SELECT COALESCE(MAX(number), 0) FROM tickets WHERE raffle_id = %s",
            (raffle_id,),
        )
        max_number = cur.fetchone()[0]
        if max_number + payload.quantity > total_tickets:
            cur.close()
            raise HTTPException(status_code=400, detail="Not enough tickets available")
        participant_id = get_or_create_participant(conn, payload.participant)
        numbers = list(range(max_number + 1, max_number + payload.quantity + 1))
        ticket_ids: list[uuid.UUID] = []
        for number in numbers:
            ticket_id = uuid.uuid4()
            cur.execute(
                """
                INSERT INTO tickets (id, raffle_id, participant_id, number, status)
                VALUES (%s, %s, %s, %s, 'paid')
                """,
                (ticket_id, raffle_id, participant_id, number),
            )
            ticket_ids.append(ticket_id)
        if max_number + payload.quantity == total_tickets:
            cur.execute(
                "UPDATE raffles SET status = 'closed', updated_at = now() WHERE id = %s",
                (raffle_id,),
            )
        cur.close()
        return {
            "raffle_id": str(raffle_id),
            "participant_id": str(participant_id),
            "ticket_ids": [str(ticket_id) for ticket_id in ticket_ids],
            "numbers": numbers,
            "total_price": ticket_price * payload.quantity,
            "currency": currency,
        }

    return run_transaction(_handler)
