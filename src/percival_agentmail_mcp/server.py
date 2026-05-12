import argparse
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

from mcp.server.fastmcp import FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import load_config
from percival_agentmail_mcp.tools import register_tools

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("percival_agentmail_mcp")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict]:
    """Server lifespan manager to handle AgentMail client lifecycle."""
    config = load_config()
    wrapper = AgentMailClientWrapper(api_key=config.api_key, timeout=config.timeout)
    
    logger.info(f"Initializing AgentMail MCP server for inbox: {config.inbox_id}")
    
    try:
        yield {
            "agentmail_client": wrapper,
            "config": config,
        }
    finally:
        logger.info("Shutting down AgentMail MCP server...")
        # The underlying httpx.AsyncClient is managed by the SDK and will be garbage collected

def create_server(debug: bool = False) -> FastMCP:
    """Create and configure the MCP server."""
    if debug:
        logger.setLevel(logging.DEBUG)
        
    server = FastMCP(
        "percival-agentmail",
        lifespan=server_lifespan,
    )
    
    register_tools(server)
    return server

def main() -> None:
    """Run the AgentMail MCP server."""
    parser = argparse.ArgumentParser(description="Percival AgentMail MCP Server")
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="store_true", help="Show version information and exit")
    args = parser.parse_args()
    
    if args.version:
        from percival_agentmail_mcp import __version__
        print(f"Percival AgentMail MCP Server version {__version__}")
        return
    
    server = create_server(args.debug)
    logger.info("Starting server{}...".format(" in development mode" if args.dev else ""))
    
    if args.dev:
        # Dev mode typically runs with specific inspector settings if needed, 
        # but fastmcp dev command is usually preferred
        server.run()
    else:
        server.run()

if __name__ == "__main__":
    main()
