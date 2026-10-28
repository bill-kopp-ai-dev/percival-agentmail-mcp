"""Tests for ServerConfig (Fase 1 — config security)."""

from pathlib import Path

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
    # ``_env_file=None`` disables Pydantic-Settings' default search for a
    # ``.env`` file in ``cwd``. Without this, a developer's local ``.env``
    # leaks values like ``AGENTMAIL_MAX_RESULTS=50`` into the assertion
    # ``max_results == 25`` below. Tests must be hermetic.
    return ServerConfig(
        _env_file=None,
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


def test_config_loads_api_key_from_mounted_file(tmp_path: Path) -> None:
    key_file = tmp_path / "agentmail-api-key"
    key_file.write_text("am_file_secret_for_test\n", encoding="utf-8")

    cfg = ServerConfig(_env_file=None, api_key_file=key_file, inbox_id="file@agentmail.to")

    assert cfg.api_key == "am_file_secret_for_test"
    assert "am_file_secret_for_test" not in repr(cfg)
    assert "am_file_secret_for_test" not in str(cfg.model_dump())


def test_config_rejects_symlinked_api_key_file(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("am_file_secret_for_test", encoding="utf-8")
    link = tmp_path / "api-key"
    link.symlink_to(target)

    with pytest.raises(ValidationError, match="regular file"):
        ServerConfig(_env_file=None, api_key_file=link, inbox_id="file@agentmail.to")


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


def test_load_config_missing_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # ``monkeypatch.chdir`` puts us in an empty tempdir so Pydantic-Settings
    # does not find a stray ``.env`` file (the developer's local one would
    # otherwise satisfy the required env vars and mask the missing-env path).
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    monkeypatch.delenv("AGENTMAIL_INBOX_ID", raising=False)
    with caplog.at_level("ERROR"), pytest.raises(ValueError) as exc:
        load_config()
    assert "Missing or invalid" in str(exc.value)
    # Mensagem não deve vazar nada da chave
    assert "am_" not in str(exc.value)
    assert all(record.exc_info is None for record in caplog.records)


def test_load_config_logs_without_secret(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("AGENTMAIL_API_KEY", "am_test_12345678")
    monkeypatch.setenv("AGENTMAIL_INBOX_ID", "agent@agentmail.to")
    with caplog.at_level("INFO"):
        config = load_config()
    for record in caplog.records:
        assert "am_test_12345678" not in record.getMessage()
        assert config.inbox_id not in record.getMessage()


def test_load_config_ignores_ambient_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "AGENTMAIL_API_KEY=am_ambient_secret\nAGENTMAIL_INBOX_ID=ambient@agentmail.to\n", encoding="utf-8"
    )
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    monkeypatch.delenv("AGENTMAIL_INBOX_ID", raising=False)
    monkeypatch.delenv("AGENTMAIL_ENV_FILE", raising=False)

    with pytest.raises(ValueError, match="Missing or invalid"):
        load_config()


def test_load_config_reads_explicit_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / "selected.env"
    env_file.write_text(
        "AGENTMAIL_API_KEY=am_explicit_secret\nAGENTMAIL_INBOX_ID=selected@agentmail.to\n", encoding="utf-8"
    )
    monkeypatch.setenv("AGENTMAIL_ENV_FILE", str(env_file))
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    monkeypatch.delenv("AGENTMAIL_INBOX_ID", raising=False)

    config = load_config()

    assert config.api_key == "am_explicit_secret"
    assert config.inbox_id == "selected@agentmail.to"
