import json
import logging
from typing import Any, Dict, List, Optional

from agentmail import AsyncAgentMail
from agentmail.core.api_error import ApiError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AgentMailClientWrapper:
    """Wrapper around the official AsyncAgentMail SDK to simplify MCP integration."""
    
    def __init__(self, api_key: str, timeout: int = 30):
        """Initialize the async client."""
        self.client = AsyncAgentMail(api_key=api_key, timeout=timeout)
        
    def _serialize(self, obj: Any) -> Any:
        """Serialize SDK objects (Pydantic models) to JSON-friendly dicts."""
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json", exclude_none=True)
        elif isinstance(obj, list):
            return [self._serialize(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        return obj

    def format_response(self, obj: Any) -> str:
        """Format a successful response to a JSON string."""
        serialized = self._serialize(obj)
        return json.dumps(serialized, indent=2)

    def format_error(self, e: Exception) -> str:
        """Format an exception into a safe error message for the LLM.
        
        HIGH-02: Only expose sanitized, mapped error messages to prevent
        leaking internal details (tokens, paths, stack traces).
        """
        if isinstance(e, ApiError):
            status_code = e.status_code
            # Log the full error details internally for debugging
            logger.error(f"AgentMail API Error {status_code}: {e.body}")
            
            # HIGH-02: Map status codes to safe, generic messages
            safe_messages = {
                400: "Bad request — check the parameters provided.",
                401: "Authentication failed — API key may be invalid or expired.",
                403: "Permission denied for the requested operation.",
                404: "The requested resource was not found.",
                409: "Conflict — the resource may already exist.",
                422: "Validation error — check the format of the data provided.",
                429: "Rate limit exceeded — wait a moment and try again.",
                500: "AgentMail internal server error — try again later.",
                502: "AgentMail service temporarily unavailable.",
                503: "AgentMail service temporarily unavailable.",
            }
            message = safe_messages.get(status_code, f"API error (HTTP {status_code}).")
            return json.dumps({
                "status": "error",
                "code": status_code,
                "message": message
            }, indent=2)
        
        # Log full exception internally, but only expose a generic message
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": "An internal error occurred. Check server logs for details."
        }, indent=2)
