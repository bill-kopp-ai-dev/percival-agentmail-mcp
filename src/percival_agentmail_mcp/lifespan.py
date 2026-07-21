"""Typed lifespan context for the AgentMail MCP server.

A frozen dataclass is passed through ``ctx.request_context.lifespan_context``
to every tool. Tools access it via ``get_context(ctx)`` or via the
``@with_agentmail`` decorator (introduced in Fase 4).
"""

from dataclasses import dataclass

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig


@dataclass(frozen=True)
class LifespanContext:
    """Immutable context handed to every tool.

    Attributes:
        client: Wrapped AgentMail SDK with retry, rate limiting and
            sanitized error formatting.
        config: Validated server configuration.
    """

    client: AgentMailClientWrapper
    config: ServerConfig
