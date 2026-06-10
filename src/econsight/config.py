import logging
from typing import cast

import structlog
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/econsight",
        validation_alias=AliasChoices("DB_URL", "DATABASE_URL"),
    )
    log_level: str = "INFO"
    # Trailing slash required for correct httpx base_url path merging
    statcan_base_url: str = "https://www150.statcan.gc.ca/t1/wds/rest/"
    boc_base_url: str = "https://www.bankofcanada.ca/valet/"
    http_timeout: float = 30.0
    http_max_retries: int = 5
    cors_origins: list[str] = ["http://localhost:5173"]
    db_url_readonly: str = Field(
        default="postgresql://postgres:password@localhost:5432/econsight",
        validation_alias=AliasChoices("DB_URL_READONLY", "DATABASE_URL"),
    )
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    auto_seed: bool = False
    auto_seed_models: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


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
