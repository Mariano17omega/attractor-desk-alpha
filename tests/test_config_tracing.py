"""Tests for configuration loading and tracing setup."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import core.config as config
from core import tracing


@pytest.fixture
def reset_config_state() -> None:
    original_config = config._config.copy()
    original_loaded = config._config_loaded
    yield
    config._config = original_config
    config._config_loaded = original_loaded


def test_load_config_from_file(tmp_path: Path, reset_config_state: None) -> None:
    config_path = tmp_path / "API_KEY.txt"
    config_path.write_text(
        "\n".join(
            [
                "# comment",
                "OPENROUTER_API_KEY='abc-123'",
                "EXA_API_KEY=exa-key",
                "INVALID_LINE",
            ]
        ),
        encoding="utf-8",
    )

    result = config.load_config(config_path)

    assert result["OPENROUTER_API_KEY"] == "abc-123"
    assert result["EXA_API_KEY"] == "exa-key"
    assert config.get_api_key("OPENROUTER_API_KEY") == "abc-123"


def test_load_config_from_env_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_config_state: None
) -> None:
    missing_path = tmp_path / "missing.txt"
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")

    result = config.load_config(missing_path)

    assert result["OPENROUTER_API_KEY"] == "env-key"


def test_get_openrouter_api_key_raises_when_missing(reset_config_state: None) -> None:
    config._config = {}
    config._config_loaded = True

    with pytest.raises(ValueError):
        config.get_openrouter_api_key()


def test_setup_langsmith_tracing_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tracing, "is_langsmith_enabled", lambda: True)
    monkeypatch.setattr(tracing, "get_langsmith_api_key", lambda: "ls-key")
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_ENDPOINT", raising=False)

    enabled = tracing.setup_langsmith_tracing(project_name="proj")

    assert enabled is True
    assert os.environ["LANGCHAIN_PROJECT"] == "proj"
    assert os.environ["LANGCHAIN_API_KEY"] == "ls-key"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"


def test_setup_langsmith_tracing_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAIN_API_KEY", "old-key")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")

    enabled = tracing.setup_langsmith_tracing(enabled=False)

    assert enabled is False
    assert "LANGCHAIN_TRACING_V2" not in os.environ
    assert "LANGCHAIN_API_KEY" not in os.environ


def test_get_run_url_uses_project_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAIN_PROJECT", "custom-project")
    url = tracing.get_run_url("run-123")

    assert url.endswith("/custom-project/r/run-123")
