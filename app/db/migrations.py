from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from shutil import which
from urllib.parse import quote

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


def deploy_migrations() -> None:
    global _MIGRATIONS_READY
    with _MIGRATIONS_LOCK:
        _run_sqitch("deploy")
        _MIGRATIONS_READY = True


def ensure_migrations() -> None:
    global _MIGRATIONS_READY
    if _MIGRATIONS_READY:
        return
    with _MIGRATIONS_LOCK:
        if _MIGRATIONS_READY:
            return
        _run_sqitch("deploy")
        _MIGRATIONS_READY = True
