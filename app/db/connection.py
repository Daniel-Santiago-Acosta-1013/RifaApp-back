from __future__ import annotations

import threading
from typing import Callable, Optional

import pg8000.dbapi as pgapi

from app.core.config import db_configured, settings
from app.db.migrations import ensure_migrations

_DB_LOCAL = threading.local()


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
        ensure_migrations()
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
            ensure_migrations()
        result = handler(conn)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
