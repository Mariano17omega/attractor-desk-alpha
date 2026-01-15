"""Tests for configuration loading and tracing setup."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import core.config as config
from core import tracing


@pytest.fixture
def reset_config_state() -> None:
    """Reset config module state before and after tests."""
    original_config = config._config.copy()
    original_loaded = config._config_loaded
    original_keyring = config._keyring_service
    yield
    config._config = original_config
    config._config_loaded = original_loaded
    config._keyring_service = original_keyring


@pytest.fixture
def mock_keyring_unavailable():
    """Mock keyring as unavailable for legacy file tests."""
    mock_service = MagicMock()
    mock_service.is_available = False
    mock_service.get_credential.return_value = None
    mock_service.get_all_credentials.return_value = {
        "openrouter": None,
        "exa": None,
        "firecrawl": None,
        "langsmith": None,
    }
    with patch.object(config, "_keyring_service", mock_service):
        with patch("core.config._get_keyring", return_value=mock_service):
            yield mock_service


def test_load_config_from_file(
    tmp_path: Path, reset_config_state: None, mock_keyring_unavailable
) -> None:
    """Test loading config from API_KEY.txt file."""
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
    
    # Clear existing config
    config._config = {}
    config._config_loaded = False

    result = config.load_config(config_path)

    assert result["OPENROUTER_API_KEY"] == "abc-123"
    assert result["EXA_API_KEY"] == "exa-key"


def test_load_config_from_env_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_config_state: None,
    mock_keyring_unavailable
) -> None:
    """Test falling back to environment variables when file is missing."""
    missing_path = tmp_path / "missing.txt"
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
    
    # Clear existing config
    config._config = {}
    config._config_loaded = False

    result = config.load_config(missing_path)

    assert result["OPENROUTER_API_KEY"] == "env-key"


def test_get_openrouter_api_key_raises_when_missing(
    reset_config_state: None, mock_keyring_unavailable, tmp_path: Path
) -> None:
    """Test that get_openrouter_api_key raises when key is not configured."""
    config._config = {}
    config._config_loaded = True
    
    # Mock get_config_path to return a non-existent file
    nonexistent_path = tmp_path / "nonexistent_api_key.txt"
    
    with patch.object(config, "get_config_path", return_value=nonexistent_path):
        # Ensure no env var fallback
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                config.get_openrouter_api_key()


def test_get_api_key_from_keyring(reset_config_state: None) -> None:
    """Test that API keys are retrieved from keyring first."""
    mock_service = MagicMock()
    mock_service.is_available = True
    mock_service.get_credential.return_value = "keyring-key-123"
    
    with patch("core.config._get_keyring", return_value=mock_service):
        result = config.get_api_key("OPENROUTER_API_KEY")
    
    assert result == "keyring-key-123"
    mock_service.get_credential.assert_called_with("openrouter")


def test_get_api_key_env_fallback(reset_config_state: None) -> None:
    """Test that env vars are used when keyring is empty."""
    mock_service = MagicMock()
    mock_service.is_available = True
    mock_service.get_credential.return_value = None
    
    with patch("core.config._get_keyring", return_value=mock_service):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key-456"}):
            result = config.get_api_key("OPENROUTER_API_KEY")
    
    assert result == "env-key-456"


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
