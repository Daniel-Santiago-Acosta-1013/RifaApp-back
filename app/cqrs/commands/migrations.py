from __future__ import annotations

from datetime import datetime, timezone
import logging

from fastapi import HTTPException

from app.db.migrations import deploy_migrations

logger = logging.getLogger(__name__)


def run_migrations() -> dict:
    try:
        deploy_migrations()
    except Exception as exc:
        logger.exception("Migration run failed")
        raise HTTPException(status_code=500, detail="Migration failed. Check logs.") from exc
    return {"status": "ok", "applied_at": datetime.now(timezone.utc)}
