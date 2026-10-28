"""Server entry point for Percival AgentMail MCP.

Manages the AgentMail client lifecycle via FastMCP's lifespan hook:

- On startup: build the client, run a health check (HIGH-03), yield a
  ``LifespanContext``.
- On shutdown: close the underlying ``httpx.AsyncClient`` to drain
  connections cleanly (HIGH-03).
"""

import argparse
import logging
import signal
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio
from agentmail.core.api_error import ApiError
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

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
SIGNAL_DRAIN_SECONDS = 2
SHUTDOWN_TIMEOUT_SECONDS = 5


class AgentMailFastMCP(FastMCP):
    """FastMCP stdio transport with graceful signal-driven lifespan shutdown."""

    async def run_stdio_async(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            async with anyio.create_task_group() as task_group:

                async def serve() -> None:
                    try:
                        await self._mcp_server.run(
                            read_stream,
                            write_stream,
                            self._mcp_server.create_initialization_options(),
                        )
                    finally:
                        task_group.cancel_scope.cancel()

                async def watch_termination_signals() -> None:
                    with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
                        logger.info("Termination signal handlers active")
                        async for received_signal in signals:
                            logger.info(
                                "Received %s; allowing up to %s seconds for in-flight work",
                                received_signal.name,
                                SIGNAL_DRAIN_SECONDS,
                            )
                            await anyio.sleep(SIGNAL_DRAIN_SECONDS)
                            logger.info("Shutdown grace window ended; cancelling remaining MCP work")
                            task_group.cancel_scope.cancel()
                            return

                task_group.start_soon(serve)
                task_group.start_soon(watch_termination_signals)


async def _close_client_bounded(wrapper: AgentMailClientWrapper) -> None:
    """Close the HTTP pool despite cancellation, with a hard upper bound."""
    with anyio.CancelScope(shield=True):
        with anyio.move_on_after(SHUTDOWN_TIMEOUT_SECONDS) as timeout_scope:
            try:
                await wrapper.aclose()
            except Exception as exc:
                logger.warning("Error while closing AgentMail client (%s)", type(exc).__name__)
        if timeout_scope.cancel_called:
            logger.warning("Timed out closing AgentMail client after %s seconds", SHUTDOWN_TIMEOUT_SECONDS)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[LifespanContext]:
    """Manage the AgentMail client lifecycle.

    - Validates connectivity on startup via ``mail_get_inbox_info``
      (with retry/backoff for transient failures).
    - Closes the underlying ``httpx.AsyncClient`` on shutdown (HIGH-03).
    """
    config = load_config()
    wrapper = AgentMailClientWrapper(api_key=config.api_key, timeout=config.timeout)
    logger.info("Initializing AgentMail MCP server")

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
        await _close_client_bounded(wrapper)
        raise RuntimeError(
            f"Cannot reach AgentMail API at startup (HTTP {status}). Verify AGENTMAIL_API_KEY and AGENTMAIL_INBOX_ID."
        ) from e
    except Exception as exc:
        logger.error("Unexpected error during AgentMail health check (%s)", type(exc).__name__)
        await _close_client_bounded(wrapper)
        raise

    try:
        yield LifespanContext(client=wrapper, config=config)
    finally:
        logger.info("Shutting down AgentMail MCP server...")
        # HIGH-03: fechar explicitamente para drenar conexões
        await _close_client_bounded(wrapper)


def create_server(debug: bool = False) -> FastMCP:
    """Create and configure the MCP server."""
    if debug:
        logger.setLevel(logging.DEBUG)

    server = AgentMailFastMCP(
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
    try:
        server.run()
    except Exception as exc:
        if args.debug:
            logger.exception("AgentMail MCP server stopped unexpectedly")
        else:
            logger.error("AgentMail MCP server stopped (%s)", type(exc).__name__)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
