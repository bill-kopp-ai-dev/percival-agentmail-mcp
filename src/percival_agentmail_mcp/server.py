"""Server entry point for Percival AgentMail MCP.

Manages the AgentMail client lifecycle via FastMCP's lifespan hook:

- On startup: build the client, run a health check (HIGH-03), yield a
  ``LifespanContext``.
- On shutdown: close the underlying ``httpx.AsyncClient`` to drain
  connections cleanly (HIGH-03).
"""

import argparse
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from agentmail.core.api_error import ApiError
from mcp.server.fastmcp import FastMCP

from percival_agentmail_mcp import __version__
from percival_agentmail_mcp.client import AgentMailClientWrapper, with_retry
from percival_agentmail_mcp.config import load_config
from percival_agentmail_mcp.lifespan import LifespanContext
from percival_agentmail_mcp.prompts import register_prompts
from percival_agentmail_mcp.tools import register_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("percival_agentmail_mcp")


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[LifespanContext]:
    """Manage the AgentMail client lifecycle.

    - Validates connectivity on startup via ``mail_get_inbox_info``
      (with retry/backoff for transient failures).
    - Closes the underlying ``httpx.AsyncClient`` on shutdown (HIGH-03).
    """
    config = load_config()
    wrapper = AgentMailClientWrapper(api_key=config.api_key, timeout=config.timeout)
    logger.info("Initializing AgentMail MCP server for inbox: %s", config.inbox_id)

    # LOW-08: validar saúde do cliente no startup, com retry/backoff para
    # tolerar instabilidades transitórias (429/5xx).
    try:
        await with_retry(
            lambda: wrapper.client.inboxes.get(inbox_id=config.inbox_id),
        )
        logger.info("AgentMail health check OK")
    except ApiError as e:
        status = e.status_code if e.status_code is not None else "unknown"
        logger.error("AgentMail health check failed (HTTP %s)", status)
        await wrapper.client.aclose()
        raise RuntimeError(
            f"Cannot reach AgentMail API at startup (HTTP {status}). Verify AGENTMAIL_API_KEY and AGENTMAIL_INBOX_ID."
        ) from e
    except Exception:
        logger.error("Unexpected error during AgentMail health check", exc_info=True)
        await wrapper.client.aclose()
        raise

    try:
        yield LifespanContext(client=wrapper, config=config)
    finally:
        logger.info("Shutting down AgentMail MCP server...")
        # HIGH-03: fechar explicitamente para drenar conexões
        try:
            await wrapper.client.aclose()
        except Exception:
            logger.warning("Error while closing AgentMail client", exc_info=True)


def create_server(debug: bool = False) -> FastMCP:
    """Create and configure the MCP server."""
    if debug:
        logger.setLevel(logging.DEBUG)

    server = FastMCP(
        "percival-agentmail",
        lifespan=server_lifespan,
    )
    register_tools(server)
    register_prompts(server)
    return server


def main() -> None:
    """Run the AgentMail MCP server."""
    parser = argparse.ArgumentParser(description="Percival AgentMail MCP Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"Percival AgentMail MCP Server version {__version__}")
        return

    server = create_server(args.debug)
    logger.info("Starting server...")
    server.run()


if __name__ == "__main__":
    main()
