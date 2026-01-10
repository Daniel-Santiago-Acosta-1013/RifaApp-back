from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Optional

from fastapi import HTTPException

from app.db.connection import fetch_all, fetch_one


def _normalize_status(status: Optional[str]) -> Optional[str]:
    if not status:
        return None
    normalized = status.lower().strip()
    if normalized == "published":
        return "open"
    return normalized


def _raffle_row(row: dict) -> dict:
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
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_raffles(status: Optional[str] = None) -> list[dict]:
    normalized = _normalize_status(status)
    sql = """
        SELECT r.id, r.title, r.description, r.ticket_price, r.currency, r.total_tickets,
               r.status, r.draw_at, r.winner_ticket_id, r.number_start, r.number_end,
               r.number_padding, r.created_at, r.updated_at,
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
    """
    params: tuple = ()
    if normalized:
        sql += " WHERE r.status = %s"
        params = (normalized,)
    sql += " ORDER BY r.created_at DESC"
    rows = fetch_all(sql, params)
    return [_raffle_row(row) for row in rows]


def get_raffle(raffle_id: uuid.UUID) -> dict:
    row = fetch_one(
        """
        SELECT r.id, r.title, r.description, r.ticket_price, r.currency, r.total_tickets,
               r.status, r.draw_at, r.winner_ticket_id, r.number_start, r.number_end,
               r.number_padding, r.created_at, r.updated_at,
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
    if not row:
        raise HTTPException(status_code=404, detail="Raffle not found")
    return _raffle_row(row)


def list_numbers(raffle_id: uuid.UUID, offset: int = 0, limit: Optional[int] = None) -> dict:
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be >= 0")
    raffle = fetch_one(
        """
        SELECT id, total_tickets, number_start, number_end, number_padding, status
        FROM raffles_read
        WHERE id = %s
        """,
        (raffle_id,),
    )
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")
    total_tickets = raffle["total_tickets"]
    raw_number_start = raffle.get("number_start")
    number_start = 1 if raw_number_start is None else raw_number_start
    raw_number_end = raffle.get("number_end")
    number_end = (number_start + total_tickets - 1) if raw_number_end is None else raw_number_end
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
        SELECT number, status, reserved_until, label
        FROM raffle_numbers_read
        WHERE raffle_id = %s AND number BETWEEN %s AND %s
        ORDER BY number ASC
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
            "label": row.get("label"),
        }
    padding = raffle.get("number_padding")
    numbers = []
    counts = {"available": 0, "reserved": 0, "sold": 0}
    for number in range(start_number, end_number + 1):
        ticket = status_by_number.get(number)
        if not ticket:
            status = "available"
            reserved_until = None
            label = str(number).zfill(padding) if padding else str(number)
        else:
            status = ticket["status"]
            if status == "reserved":
                reserved_until = ticket.get("reserved_until")
            else:
                reserved_until = None
            label = ticket.get("label") or (str(number).zfill(padding) if padding else str(number))
        counts[status] = counts.get(status, 0) + 1
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
