"""Percival AgentMail MCP server package."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("percival-agentmail-mcp")
except PackageNotFoundError:
    # Package not installed (e.g. running from a source checkout without
    # `pip install -e .`) — fall back to a literal so imports don't crash.
    __version__ = "0.0.0"
