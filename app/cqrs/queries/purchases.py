from __future__ import annotations

import uuid

from app.db.connection import fetch_all


def list_purchases(participant_id: uuid.UUID) -> list[dict]:
    rows = fetch_all(
        """
        SELECT purchase_id, raffle_id, participant_id, raffle_title, raffle_status,
               numbers, total_price, currency, status, payment_method, created_at
        FROM purchases_read
        WHERE participant_id = %s
        ORDER BY created_at DESC
        """,
        (participant_id,),
    )
    purchases: list[dict] = []
    for row in rows:
        numbers = row.get("numbers") or []
        if isinstance(numbers, tuple):
            numbers = list(numbers)
        elif isinstance(numbers, str):
            raw = numbers.strip("{}")
            numbers = [int(value) for value in raw.split(",") if value]
        purchases.append(
            {
                "purchase_id": str(row["purchase_id"]),
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
