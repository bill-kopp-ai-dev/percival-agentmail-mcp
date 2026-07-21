"""Configuration for the AgentMail MCP server.

Hardened with Pydantic validators so invalid configuration is rejected
at startup, never at runtime. Sensitive values are masked in any
``repr``, ``str`` or ``model_dump`` to prevent accidental leakage.
"""

import logging
from typing import Any

from pydantic import EmailStr, Field
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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LOW-01: bloqueia repr/str padrão que poderiam vazar a api_key
    def __repr__(self) -> str:
        return f"ServerConfig(inbox_id={self.inbox_id!r}, api_key=****)"

    def __str__(self) -> str:
        return self.__repr__()

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        """Override to mask api_key even in model_dump output."""
        data = super().model_dump(**kwargs)
        if "api_key" in data:
            data["api_key"] = "****"
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
        config = ServerConfig()
    except Exception:
        # Log estruturado para diagnóstico, sem vazar o valor da chave.
        logger.error("Failed to load AgentMail configuration", exc_info=True)
        raise ValueError(
            "Missing or invalid AgentMail configuration. "
            "Ensure AGENTMAIL_API_KEY (>=8 chars) and AGENTMAIL_INBOX_ID "
            "(valid email) are set in the environment or .env file."
        ) from None

    logger.info("Loaded configuration for inbox: %s", config.inbox_id)
    return config
