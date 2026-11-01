"""Configuration for the AgentMail MCP server.

Hardened with Pydantic validators so invalid configuration is rejected
at startup, never at runtime. Sensitive values are masked in any
``repr``, ``str`` or ``model_dump`` to prevent accidental leakage.
"""

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import EmailStr, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# MED-02: defensive hard caps to prevent resource exhaustion
MAX_RESULTS_HARD_CAP = 50
TIMEOUT_HARD_CAP = 120  # seconds


class ServerConfig(BaseSettings):
    """Configuration for the AgentMail MCP server.

    All fields are loaded from environment variables with the prefix
    ``AGENTMAIL_`` (e.g. ``AGENTMAIL_API_KEY``). Missing or invalid
    values raise ``ValidationError`` at construction time.
    """

    api_key: str = Field(
        ...,
        min_length=8,
        description="AgentMail API key. Must have at least 8 characters.",
    )
    api_key_file: Path | None = Field(
        default=None,
        description="Optional mounted file containing the AgentMail API key.",
    )
    inbox_id_file: Path | None = Field(
        default=None,
        description="Optional mounted file containing the default inbox identifier.",
    )
    inbox_id: EmailStr = Field(
        ...,
        description="Default inbox identifier used by all tools.",
    )
    max_results: int = Field(
        default=25,
        ge=1,
        le=MAX_RESULTS_HARD_CAP,
        description=f"Max items per list call. Hard-capped at {MAX_RESULTS_HARD_CAP}.",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=TIMEOUT_HARD_CAP,
        description=f"HTTP timeout in seconds. Hard-capped at {TIMEOUT_HARD_CAP}.",
    )

    model_config = SettingsConfigDict(
        env_prefix="AGENTMAIL_",
        # Ambient cwd files are not configuration unless explicitly selected.
        env_file=None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def load_api_key_file(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        resolved = dict(values)
        for value_name, file_name in (("api_key", "api_key_file"), ("inbox_id", "inbox_id_file")):
            if resolved.get(value_name) or not resolved.get(file_name):
                continue
            path = Path(resolved[file_name])
            env_name = f"AGENTMAIL_{file_name.upper()}"
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"{env_name} must refer to a regular file")
            value = path.read_text(encoding="utf-8").strip()
            if not value:
                raise ValueError(f"{env_name} is empty")
            resolved[value_name] = value
        return resolved

    # Bloqueia repr/str padrão que poderiam vazar valores sensíveis.
    def __repr__(self) -> str:
        return "ServerConfig(api_key=****, inbox_id=****)"

    def __str__(self) -> str:
        return self.__repr__()

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        """Mask credentials and inbox identifiers in model_dump output."""
        data = super().model_dump(**kwargs)
        for field in ("api_key", "inbox_id"):
            if field in data:
                data[field] = "****"
        return data


def load_config() -> ServerConfig:
    """Load configuration from environment variables.

    Returns:
        A validated ``ServerConfig``.

    Raises:
        ValueError: when required env vars are missing or invalid.
            The original Pydantic error is chained for diagnostics.
    """
    try:
        config = ServerConfig(_env_file=os.environ.get("AGENTMAIL_ENV_FILE"))
    except Exception:
        # Log estruturado para diagnóstico, sem vazar o valor da chave.
        logger.error("Failed to load AgentMail configuration (invalid or missing settings)")
        raise ValueError(
            "Missing or invalid AgentMail configuration. "
            "Ensure AGENTMAIL_API_KEY (>=8 chars) or AGENTMAIL_API_KEY_FILE and "
            "AGENTMAIL_INBOX_ID (valid email) or AGENTMAIL_INBOX_ID_FILE are set."
        ) from None

    logger.info("Loaded AgentMail configuration")
    return config
