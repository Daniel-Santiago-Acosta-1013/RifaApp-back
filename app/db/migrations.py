from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from shutil import which
from urllib.parse import quote

import pg8000.dbapi as pgapi

from app.core.config import db_configured, settings

_MIGRATIONS_READY = False
_MIGRATIONS_LOCK = threading.Lock()


def _resolve_sqitch() -> str:
    sqitch_bin = os.getenv("SQITCH_BIN", "sqitch")
    candidate = Path(sqitch_bin)
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    resolved = which(sqitch_bin)
    if resolved:
        return resolved
    raise RuntimeError("Sqitch not found. Install it and ensure it is in PATH.")


def _build_target() -> tuple[str, dict]:
    target = os.getenv("SQITCH_TARGET")
    if target:
        return target, {}
    if not db_configured():
        raise RuntimeError("Database configuration is missing")
    user = quote(settings.db_user, safe="")
    dbname = quote(settings.db_name, safe="")
    target = f"db:pg://{user}@{settings.db_host}:{settings.db_port}/{dbname}"
    return target, {"PGPASSWORD": settings.db_password}


def _run_sqitch(command: str) -> None:
    sqitch_cmd = _resolve_sqitch()
    target, extra_env = _build_target()
    env = os.environ.copy()
    env.update(extra_env)
    repo_root = Path(os.getenv("SQITCH_DIR", Path(__file__).resolve().parents[2])).resolve()
    subprocess.run(
        [sqitch_cmd, command, "--target", target],
        cwd=str(repo_root),
        env=env,
        check=True,
    )


def _connect_direct():
    if not db_configured():
        raise RuntimeError("Database configuration is missing")
    return pgapi.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )


def _load_plan_entries(repo_root: Path) -> list[str]:
    plan_path = repo_root / "sqitch.plan"
    if not plan_path.exists():
        raise RuntimeError("sqitch.plan not found for fallback migrations")
    entries: list[str] = []
    for raw in plan_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("%") or line.startswith("#"):
            continue
        name = line.split()[0]
        entries.append(name)
    if not entries:
        raise RuntimeError("No migrations found in sqitch.plan")
    return entries


def _run_sql_migrations() -> None:
    repo_root = Path(os.getenv("SQITCH_DIR", Path(__file__).resolve().parents[2])).resolve()
    deploy_dir = repo_root / "sqitch" / "deploy"
    entries = _load_plan_entries(repo_root)
    conn = _connect_direct()
    try:
        conn.autocommit = True
        cur = conn.cursor()
        for name in entries:
            sql_path = deploy_dir / f"{name}.sql"
            if not sql_path.exists():
                raise RuntimeError(f"Missing migration file: {sql_path}")
            cur.execute(sql_path.read_text())
        cur.close()
    finally:
        conn.close()


def _deploy_migrations() -> None:
    try:
        _run_sqitch("deploy")
    except RuntimeError as exc:
        if "Sqitch not found" in str(exc):
            _run_sql_migrations()
            return
        raise


def deploy_migrations() -> None:
    global _MIGRATIONS_READY
    with _MIGRATIONS_LOCK:
        _deploy_migrations()
        _MIGRATIONS_READY = True


def ensure_migrations() -> None:
    global _MIGRATIONS_READY
    if _MIGRATIONS_READY:
        return
    with _MIGRATIONS_LOCK:
        if _MIGRATIONS_READY:
            return
        _deploy_migrations()
        _MIGRATIONS_READY = True
