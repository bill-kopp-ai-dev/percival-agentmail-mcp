"""Utility tools (1 tool)."""

import json
import time

from mcp.server.fastmcp import Context, FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.decorators import with_agentmail


def register(mcp: FastMCP) -> None:
    @mcp.tool("mail_get_status")
    @with_agentmail
    async def server_status(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
    ) -> str:
        """Performs a diagnostic health check, pinging the AgentMail API
        and reporting operational status and latency.
        """
        started = time.monotonic()
        api_ok = True
        api_error: str | None = None
        try:
            await client.client.inboxes.get(inbox_id=config.inbox_id)
        except Exception as e:  # noqa: BLE001 — intentional broad catch
            api_ok = False
            api_error = type(e).__name__

        latency_ms = int((time.monotonic() - started) * 1000)
        return json.dumps(
            {
                "status": "online" if api_ok else "degraded",
                "service": "Percival AgentMail MCP Server",
                "inbox": config.inbox_id,
                "api_reachable": api_ok,
                "api_latency_ms": latency_ms,
                "api_error": api_error,
            },
            indent=2,
        )
