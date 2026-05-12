import logging
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class ServerConfig(BaseSettings):
    """Configuration for the AgentMail MCP server."""
    
    api_key: str
    inbox_id: str
    max_results: int = 25
    timeout: int = 30
    
    model_config = SettingsConfigDict(
        env_prefix="AGENTMAIL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    def __repr__(self) -> str:
        """LOW-01: Prevent API key from leaking in logs/repr."""
        return f"ServerConfig(inbox_id={self.inbox_id!r}, api_key=****)"
    
    def __str__(self) -> str:
        return self.__repr__()

def load_config() -> ServerConfig:
    """Load configuration from environment variables."""
    try:
        config = ServerConfig()
        logger.info(f"Loaded configuration for inbox: {config.inbox_id}")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise ValueError(
            "Missing required configuration. Ensure AGENTMAIL_API_KEY and AGENTMAIL_INBOX_ID "
            "are set in the environment or .env file."
        ) from e
