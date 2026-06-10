import json
import logging
from typing import Any, cast

import structlog
from pydantic import AliasChoices, Field
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict
from pydantic_settings.main import PydanticBaseSettingsSource


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
