from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException

from app.db.connection import fetch_all, fetch_one, run_transaction
from app.models.schemas import RaffleCreate


def _raffle_row(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "description": row.get("description"),
        "ticket_price": row["ticket_price"],
        "currency": row["currency"],
        "total_tickets": row["total_tickets"],
        "tickets_sold": row.get("tickets_sold", 0) or 0,
        "status": row["status"],
        "draw_at": row.get("draw_at"),
        "winner_ticket_id": str(row["winner_ticket_id"]) if row.get("winner_ticket_id") else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_raffle(payload: RaffleCreate) -> dict:
    raffle_id = uuid.uuid4()
    row = fetch_one(
        """
        INSERT INTO raffles (
            id, title, description, ticket_price, currency, total_tickets, status, draw_at
        ) VALUES (%s, %s, %s, %s, %s, %s, 'open', %s)
        RETURNING id, title, description, ticket_price, currency, total_tickets, status,
                  draw_at, winner_ticket_id, created_at, updated_at
        """,
        (
            raffle_id,
            payload.title,
            payload.description,
            payload.ticket_price,
            payload.currency.upper(),
            payload.total_tickets,
            payload.draw_at,
        ),
    )
    return _raffle_row({**row, "tickets_sold": 0})


def list_raffles(status: Optional[str] = None) -> list[dict]:
    sql = """
        SELECT r.id, r.title, r.description, r.ticket_price, r.currency, r.total_tickets,
               r.status, r.draw_at, r.winner_ticket_id, r.created_at, r.updated_at,
               COALESCE(t.sold, 0) AS tickets_sold
        FROM raffles r
        LEFT JOIN (
            SELECT raffle_id, COUNT(*) AS sold
            FROM tickets
            GROUP BY raffle_id
        ) t ON t.raffle_id = r.id
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
               r.status, r.draw_at, r.winner_ticket_id, r.created_at, r.updated_at,
               COALESCE(t.sold, 0) AS tickets_sold
        FROM raffles r
        LEFT JOIN (
            SELECT raffle_id, COUNT(*) AS sold
            FROM tickets
            GROUP BY raffle_id
        ) t ON t.raffle_id = r.id
        WHERE r.id = %s
        """,
        (raffle_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Raffle not found")
    return _raffle_row(row)


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
            cur.close()
            return {
                "raffle_id": str(raffle_id),
                "winner_ticket_id": str(ticket[0]),
                "winner_participant_id": str(ticket[1]),
                "winning_number": ticket[2],
            }
        cur.execute(
            "SELECT id, participant_id, number FROM tickets WHERE raffle_id = %s ORDER BY random() LIMIT 1",
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
        cur.close()
        return {
            "raffle_id": str(raffle_id),
            "winner_ticket_id": str(ticket_id),
            "winner_participant_id": str(participant_id),
            "winning_number": number,
        }

    return run_transaction(_handler)
