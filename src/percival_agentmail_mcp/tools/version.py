"""Version / status utility tool (1 tool).

Provides ``mail_get_version`` (S7 from the 2026-07-21 incident report):
returns the installed package version, the server name and the
python/platform metadata — useful for troubleshooting "am I talking to
the right server?".
"""

import json
import platform
import sys

from mcp.server.fastmcp import Context, FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.decorators import with_agentmail


def _resolve_package_version() -> str:
    """Best-effort package version lookup with hardcoded fallback."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("percival-agentmail-mcp")
    except (PackageNotFoundError, Exception):
        from percival_agentmail_mcp import __version__

        return __version__


def register(mcp: FastMCP) -> None:
    @mcp.tool("mail_get_version")
    @with_agentmail
    async def get_version(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
    ) -> str:
        """Returns server version metadata: package_version, server_name, python_version, platform, inbox."""
        return json.dumps(
            {
                "package_version": _resolve_package_version(),
                "server_name": "percival-agentmail-mcp",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": platform.platform(),
                "inbox": config.inbox_id,
            },
            indent=2,
        )
