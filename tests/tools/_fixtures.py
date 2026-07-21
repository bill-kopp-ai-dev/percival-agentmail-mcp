"""Shared fixtures for per-tool tests."""

import pytest

from tests.conftest import _FakeMCPContext


@pytest.fixture
def mcp_server():  # noqa: F811
    from mcp.server.fastmcp import FastMCP

    from percival_agentmail_mcp.tools import register_tools

    server = FastMCP("percival-agentmail-test")
    register_tools(server)
    return server


@pytest.fixture
def get_tool(mcp_server):  # noqa: F811
    """Return a callable that, given a tool name, returns its underlying fn.

    Using ``get_tool`` (instead of ``tool``) avoids shadowing the standard
    pytest fixture name and keeps ruff F811 happy.
    """

    def _factory(name: str):
        return mcp_server._tool_manager._tools[name].fn

    return _factory


@pytest.fixture
def fake_ctx(mock_context):
    return _FakeMCPContext(mock_context)
