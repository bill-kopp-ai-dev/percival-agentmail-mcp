"""Tests for ServerConfig (Fase 1 — config security)."""

import pytest
from pydantic import ValidationError

from percival_agentmail_mcp.config import (
    MAX_RESULTS_HARD_CAP,
    TIMEOUT_HARD_CAP,
    ServerConfig,
    load_config,
)


@pytest.fixture
def mock_config() -> ServerConfig:
    return ServerConfig(
        api_key="am_test_key_supersecret123",
        inbox_id="test@agentmail.to",
    )


# --- Initialization ---


def test_config_initialization(mock_config: ServerConfig) -> None:
    assert mock_config.api_key == "am_test_key_supersecret123"
    assert mock_config.inbox_id == "test@agentmail.to"
    assert mock_config.max_results == 25
    assert mock_config.timeout == 30


def test_config_rejects_short_api_key() -> None:
    with pytest.raises(ValidationError):
        ServerConfig(api_key="short", inbox_id="agent@agentmail.to")


def test_config_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        ServerConfig(api_key="am_test_12345678", inbox_id="not-an-email")


def test_config_rejects_zero_max_results() -> None:
    with pytest.raises(ValidationError):
        ServerConfig(
            api_key="am_test_12345678",
            inbox_id="agent@agentmail.to",
            max_results=0,
        )


def test_config_caps_max_results_above_hard_limit() -> None:
    with pytest.raises(ValidationError):
        ServerConfig(
            api_key="am_test_12345678",
            inbox_id="agent@agentmail.to",
            max_results=MAX_RESULTS_HARD_CAP + 1,
        )


def test_config_caps_timeout_above_hard_limit() -> None:
    with pytest.raises(ValidationError):
        ServerConfig(
            api_key="am_test_12345678",
            inbox_id="agent@agentmail.to",
            timeout=TIMEOUT_HARD_CAP + 1,
        )


def test_config_rejects_zero_timeout() -> None:
    with pytest.raises(ValidationError):
        ServerConfig(
            api_key="am_test_12345678",
            inbox_id="agent@agentmail.to",
            timeout=0,
        )


def test_config_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTMAIL_API_KEY", "am_env_xxxxxxxx")
    monkeypatch.setenv("AGENTMAIL_INBOX_ID", "env@agentmail.to")
    cfg = ServerConfig()
    assert cfg.api_key == "am_env_xxxxxxxx"
    assert cfg.inbox_id == "env@agentmail.to"


# --- Secrets hygiene (LOW-01) ---


def test_config_repr_masks_api_key(mock_config: ServerConfig) -> None:
    """LOW-01: __repr__ must NEVER contain the API key."""
    text = repr(mock_config)
    assert "am_test_key_supersecret123" not in text
    assert "****" in text
    assert "test@agentmail.to" in text


def test_config_str_masks_api_key(mock_config: ServerConfig) -> None:
    """LOW-01: __str__ must NEVER contain the API key."""
    text = str(mock_config)
    assert "am_test_key_supersecret123" not in text
    assert "****" in text


def test_config_format_string_masks_api_key(mock_config: ServerConfig) -> None:
    """LOW-01: f-string formatting must also mask the key."""
    text = f"{mock_config}"
    assert "am_test_key_supersecret123" not in text


def test_config_pydantic_dict_masks_api_key(mock_config: ServerConfig) -> None:
    """LOW-01: Pydantic model_dump must mask the key."""
    dumped = mock_config.model_dump()
    assert "am_test_key_supersecret123" not in str(dumped)
    assert dumped.get("api_key") == "****"


# --- load_config ---


def test_load_config_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    monkeypatch.delenv("AGENTMAIL_INBOX_ID", raising=False)
    with pytest.raises(ValueError) as exc:
        load_config()
    assert "Missing or invalid" in str(exc.value)
    # Mensagem não deve vazar nada da chave
    assert "am_" not in str(exc.value)


def test_load_config_logs_without_secret(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("AGENTMAIL_API_KEY", "am_test_12345678")
    monkeypatch.setenv("AGENTMAIL_INBOX_ID", "agent@agentmail.to")
    with caplog.at_level("INFO"):
        load_config()
    for record in caplog.records:
        assert "am_test_12345678" not in record.getMessage()
