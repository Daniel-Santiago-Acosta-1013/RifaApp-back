from dataclasses import dataclass, field
import os


def _as_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("DB_HOST", "")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "")
    db_user: str = os.getenv("DB_USER", "")
    db_password: str = os.getenv("DB_PASSWORD", "")
    auto_migrate: bool = _as_bool(os.getenv("AUTO_MIGRATE", "false"))
    cors_allow_origins: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("CORS_ALLOW_ORIGINS", "*"))
    )
    cors_allow_methods: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("CORS_ALLOW_METHODS", "*"))
    )
    cors_allow_headers: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("CORS_ALLOW_HEADERS", "*"))
    )
    expose_errors: bool = _as_bool(os.getenv("EXPOSE_ERRORS", "true"))


settings = Settings()


def db_configured() -> bool:
    return all([settings.db_host, settings.db_name, settings.db_user, settings.db_password])
