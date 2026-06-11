from __future__ import annotations

import importlib
import os

import pytest


def _reload_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> object:
    monkeypatch.chdir(tmp_path)
    import econsight.config as config

    importlib.reload(config)
    return config.settings


def test_database_url_alias(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL", "postgres://user:pass@db.example.com:5432/railway"
    )
    settings = _reload_settings(monkeypatch, tmp_path)
    assert settings.db_url == "postgresql://user:pass@db.example.com:5432/railway"


def test_pg_env_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PGHOST", "postgres.railway.internal")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGUSER", "postgres")
    monkeypatch.setenv("PGPASSWORD", "secret")
    monkeypatch.setenv("PGDATABASE", "railway")
    settings = _reload_settings(monkeypatch, tmp_path)
    assert settings.db_url == "postgresql://postgres:secret@postgres.railway.internal:5432/railway"


def test_railway_requires_database_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    with pytest.raises(ValueError, match="Database URL not configured"):
        _reload_settings(monkeypatch, tmp_path)
