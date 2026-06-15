import logging
import os
from typing import Any, Self, cast
from urllib.parse import quote_plus

import structlog
from pydantic import AliasChoices, Field, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_LOCAL_DB_DEFAULT = "postgresql://postgres:password@localhost:5432/econsight"


def _normalize_pg_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url.removeprefix("postgres://")
    return url


def _url_from_pg_env() -> str | None:
    host = os.environ.get("PGHOST")
    if not host:
        return None
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "")
    port = os.environ.get("PGPORT", "5432")
    database = os.environ.get("PGDATABASE", "railway")
    userinfo = quote_plus(user)
    if password:
        userinfo += f":{quote_plus(password)}"
    return f"postgresql://{userinfo}@{host}:{port}/{database}"


def _is_local_default(url: str) -> bool:
    return url == _LOCAL_DB_DEFAULT or "localhost" in url or "127.0.0.1" in url


class _FlexEnvSource(EnvSettingsSource):
    """Accept plain strings and comma-separated values for list[str] fields."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        if isinstance(value, str):
            v = value.strip()
            if v and not v.startswith(("[", "{")):
                return [s.strip() for s in v.split(",") if s.strip()]
        return super().decode_complex_value(field_name, field, value)


class Settings(BaseSettings):
    db_url: str = Field(
        default=_LOCAL_DB_DEFAULT,
        validation_alias=AliasChoices(
            "DB_URL", "DATABASE_URL", "DATABASE_PUBLIC_URL", "DATABASE_PRIVATE_URL"
        ),
    )
    log_level: str = "INFO"
    # Trailing slash required for correct httpx base_url path merging
    statcan_base_url: str = "https://www150.statcan.gc.ca/t1/wds/rest/"
    boc_base_url: str = "https://www.bankofcanada.ca/valet/"
    http_timeout: float = 30.0
    http_max_retries: int = 5
    cors_origins: list[str] = ["http://localhost:5173"]
    db_url_readonly: str = Field(
        default=_LOCAL_DB_DEFAULT,
        validation_alias=AliasChoices(
            "DB_URL_READONLY",
            "DATABASE_URL",
            "DATABASE_PUBLIC_URL",
            "DATABASE_PRIVATE_URL",
        ),
    )
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    auto_seed: bool = False
    auto_seed_models: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, _FlexEnvSource(settings_cls), dotenv_settings, file_secret_settings)

    @model_validator(mode="after")
    def resolve_database_urls(self) -> Self:
        if _is_local_default(self.db_url):
            pg_url = _url_from_pg_env()
            if pg_url:
                self.db_url = pg_url
        else:
            self.db_url = _normalize_pg_url(self.db_url)

        if _is_local_default(self.db_url_readonly):
            if not _is_local_default(self.db_url):
                self.db_url_readonly = self.db_url
            else:
                pg_url = _url_from_pg_env()
                if pg_url:
                    self.db_url_readonly = pg_url
        else:
            self.db_url_readonly = _normalize_pg_url(self.db_url_readonly)

        if os.environ.get("RAILWAY_ENVIRONMENT") and _is_local_default(self.db_url):
            raise ValueError(
                "Database URL not configured. In Railway, open the backend service → "
                "Variables → New Variable → Add Reference → select PostgreSQL → DATABASE_URL."
            )

        return self


settings = Settings()


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if settings.log_level.upper() == "DEBUG":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return cast(structlog.BoundLogger, structlog.get_logger(name))
