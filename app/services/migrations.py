from __future__ import annotations

from datetime import datetime, timezone

from app.db.connection import get_conn
from app.db.schema import ensure_schema


def run_migrations() -> dict:
    conn = get_conn()
    ensure_schema(conn)
    return {"status": "ok", "applied_at": datetime.now(timezone.utc)}
