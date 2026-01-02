from dataclasses import dataclass
import os


def _as_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("DB_HOST", "")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "")
    db_user: str = os.getenv("DB_USER", "")
    db_password: str = os.getenv("DB_PASSWORD", "")
    auto_migrate: bool = _as_bool(os.getenv("AUTO_MIGRATE", "false"))


settings = Settings()


def db_configured() -> bool:
    return all([settings.db_host, settings.db_name, settings.db_user, settings.db_password])
