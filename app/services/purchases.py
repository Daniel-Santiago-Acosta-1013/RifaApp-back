from __future__ import annotations

import uuid

from app.db.connection import fetch_all


def list_purchases(participant_id: uuid.UUID) -> list[dict]:
    rows = fetch_all(
        """
        SELECT p.id, p.raffle_id, p.status, p.total_price, p.currency, p.payment_method, p.created_at,
               r.title AS raffle_title, r.status AS raffle_status
        FROM purchases p
        JOIN raffles r ON r.id = p.raffle_id
        WHERE p.participant_id = %s
        ORDER BY p.created_at DESC
        """,
        (participant_id,),
    )
    purchases: list[dict] = []
    for row in rows:
        numbers_rows = fetch_all(
            """
            SELECT number
            FROM tickets
            WHERE purchase_id = %s
            ORDER BY number ASC
            """,
            (row["id"],),
        )
        numbers = [ticket_row["number"] for ticket_row in numbers_rows]
        purchases.append(
            {
                "purchase_id": str(row["id"]),
                "raffle_id": str(row["raffle_id"]),
                "raffle_title": row["raffle_title"],
                "raffle_status": row["raffle_status"],
                "numbers": numbers,
                "total_price": row["total_price"],
                "currency": row["currency"],
                "status": row["status"],
                "payment_method": row.get("payment_method"),
                "created_at": row["created_at"],
            }
        )
    return purchases
