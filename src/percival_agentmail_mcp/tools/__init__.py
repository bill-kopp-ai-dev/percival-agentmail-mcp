"""MCP tools package.

Each submodule registers one logical group of tools via ``register(mcp)``.
The aggregator in this ``__init__`` calls them all in order.
"""

from mcp.server.fastmcp import FastMCP

from percival_agentmail_mcp.tools import drafts, inbox, messages, status, threads


def register_tools(mcp: FastMCP) -> None:
    """Register all 23 MCP tools for AgentMail API operations."""
    inbox.register(mcp)
    messages.register(mcp)
    threads.register(mcp)
    drafts.register(mcp)
    status.register(mcp)
