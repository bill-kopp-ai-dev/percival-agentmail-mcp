"""Shared pytest fixtures for the AgentMail MCP test suite."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.lifespan import LifespanContext


@pytest.fixture
def mock_config() -> ServerConfig:
    return ServerConfig(
        api_key="am_test_12345678",
        inbox_id="agent@agentmail.to",
    )


@pytest.fixture
def mock_wrapper() -> AgentMailClientWrapper:
    """A wrapper around a fully-mocked AsyncAgentMail client."""
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    wrapper.client = MagicMock()
    wrapper.client.aclose = AsyncMock()
    return wrapper


@pytest.fixture
def mock_context(mock_wrapper: AgentMailClientWrapper, mock_config: ServerConfig) -> LifespanContext:
    return LifespanContext(client=mock_wrapper, config=mock_config)


class _FakeRequestContext:
    def __init__(self, ctx_obj: LifespanContext) -> None:
        self.lifespan_context = ctx_obj


class _FakeMCPContext:
    def __init__(self, ctx_obj: LifespanContext) -> None:
        self.request_context = _FakeRequestContext(ctx_obj)


@pytest.fixture
def make_mcp_ctx(mock_context: LifespanContext):
    """Build a fake FastMCP Context carrying the lifespan_context above."""

    def _factory() -> _FakeMCPContext:
        return _FakeMCPContext(mock_context)

    return _factory


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Wipe AGENTMAIL_* env vars so tests don't leak into each other."""
    for k in (
        "AGENTMAIL_API_KEY",
        "AGENTMAIL_INBOX_ID",
        "AGENTMAIL_MAX_RESULTS",
        "AGENTMAIL_TIMEOUT",
    ):
        monkeypatch.delenv(k, raising=False)
    yield


@pytest.fixture
def mcp_server():
    """A real FastMCP server with all 23 tools registered."""
    from mcp.server.fastmcp import FastMCP

    from percival_agentmail_mcp.tools import register_tools

    server = FastMCP("percival-agentmail-test")
    register_tools(server)
    return server
