"""Inbox management tools (3 tools)."""

from mcp.server.fastmcp import Context, FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.constants import MAX_RESULTS_CAP
from percival_agentmail_mcp.decorators import retryable, with_agentmail
from percival_agentmail_mcp.helpers import cap_limit


def register(mcp: FastMCP) -> None:
    @mcp.tool("mail_get_inbox_info")
    @with_agentmail
    async def get_inbox_info(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
    ) -> str:
        """Retrieves the current configuration and statistical details of the agent's primary email inbox."""
        inbox = await client.client.inboxes.get(inbox_id=config.inbox_id)
        return client.format_response(inbox)

    @mcp.tool("mail_update_inbox")
    @with_agentmail
    async def update_inbox(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
        display_name: str | None = None,
    ) -> str:
        """Modifies the agent's primary inbox settings, allowing updates to its display name."""
        inbox = await client.client.inboxes.update(
            inbox_id=config.inbox_id,
            display_name=display_name,
        )
        return client.format_response(inbox)

    @mcp.tool("mail_list_inbox_events")
    @with_agentmail
    @retryable
    async def list_inbox_events(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
        limit: int | None = None,
    ) -> str:
        """Fetches recent event logs for the agent's inbox, useful for tracking automated actions like message delivery or receipt."""
        events = await client.client.inboxes.events.list(
            inbox_id=config.inbox_id,
            limit=cap_limit(limit, config.max_results, MAX_RESULTS_CAP),
        )
        return client.format_response(events)
