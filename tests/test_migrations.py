from pathlib import Path
from types import SimpleNamespace

import app.db.migrations as migrations


def test_build_target_uses_env_override(monkeypatch):
    monkeypatch.setenv("SQITCH_TARGET", "db:pg://override")
    target, env = migrations._build_target()
    assert target == "db:pg://override"
    assert env == {}


def test_build_target_from_settings(monkeypatch):
    monkeypatch.delenv("SQITCH_TARGET", raising=False)
    monkeypatch.setattr(migrations, "db_configured", lambda: True)
    monkeypatch.setattr(
        migrations,
        "settings",
        SimpleNamespace(
            db_user="appuser",
            db_host="localhost",
            db_port=5432,
            db_name="rifaapp",
            db_password="secret",
        ),
    )
    target, env = migrations._build_target()
    assert target == "db:pg://appuser@localhost:5432/rifaapp"
    assert env == {"PGPASSWORD": "secret"}


def test_run_sqitch_invokes_subprocess(monkeypatch, tmp_path):
    calls = {}

    def fake_run(cmd, cwd, env, check):
        calls["cmd"] = cmd
        calls["cwd"] = cwd
        calls["env"] = env
        calls["check"] = check

    monkeypatch.setattr(migrations, "_resolve_sqitch", lambda: "/usr/bin/sqitch")
    monkeypatch.setattr(
        migrations, "_build_target", lambda: ("db:pg://target", {"PGPASSWORD": "secret"})
    )
    monkeypatch.setattr(migrations.subprocess, "run", fake_run)
    monkeypatch.setenv("SQITCH_DIR", str(tmp_path))

    migrations._run_sqitch("deploy")

    assert calls["cmd"] == ["/usr/bin/sqitch", "deploy", "--target", "db:pg://target"]
    assert Path(calls["cwd"]) == tmp_path
    assert calls["env"]["PGPASSWORD"] == "secret"
    assert calls["check"] is True


def test_ensure_migrations_runs_once(monkeypatch):
    counter = {"count": 0}

    def fake_run(command):
        counter["count"] += 1

    monkeypatch.setattr(migrations, "_MIGRATIONS_READY", False)
    monkeypatch.setattr(migrations, "_run_sqitch", fake_run)

    migrations.ensure_migrations()
    migrations.ensure_migrations()

    assert counter["count"] == 1
