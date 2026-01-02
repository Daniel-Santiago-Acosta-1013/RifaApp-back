from __future__ import annotations

import threading
from typing import Callable, Optional

import pg8000.dbapi as pgapi

from app.core.config import db_configured, settings
from app.db.schema import ensure_schema

_DB_LOCAL = threading.local()
_SCHEMA_READY = False
_SCHEMA_LOCK = threading.Lock()


def _connect():
    if not db_configured():
        raise RuntimeError("Database configuration is missing")
    return pgapi.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )


def _ensure_schema(conn) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        ensure_schema(conn)
        _SCHEMA_READY = True


def get_conn():
    conn = getattr(_DB_LOCAL, "conn", None)
    if conn is None:
        conn = _connect()
        conn.autocommit = True
        _DB_LOCAL.conn = conn
    else:
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
        except Exception:
            conn = _connect()
            conn.autocommit = True
            _DB_LOCAL.conn = conn
    if settings.auto_migrate:
        _ensure_schema(conn)
    return conn


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    columns = [col[0] for col in cur.description]
    cur.close()
    return [dict(zip(columns, row)) for row in rows]


def fetch_one(sql: str, params: tuple = ()) -> Optional[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    if row is None:
        cur.close()
        return None
    columns = [col[0] for col in cur.description]
    cur.close()
    return dict(zip(columns, row))


def run_transaction(handler: Callable):
    conn = _connect()
    try:
        conn.autocommit = False
        if settings.auto_migrate:
            _ensure_schema(conn)
        result = handler(conn)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
