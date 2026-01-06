from __future__ import annotations

from datetime import datetime, timezone

from app.db.migrations import deploy_migrations


def run_migrations() -> dict:
    deploy_migrations()
    return {"status": "ok", "applied_at": datetime.now(timezone.utc)}
