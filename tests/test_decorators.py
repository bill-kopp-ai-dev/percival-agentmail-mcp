"""Tests for the @with_agentmail and @retryable decorators."""

import pytest

from percival_agentmail_mcp.decorators import retryable, with_agentmail

# --- with_agentmail signature validation ---


def test_with_agentmail_requires_ctx_first_param() -> None:
    """The first parameter MUST be named ``ctx``."""

    async def bad(client, config):
        return "x"

    with pytest.raises(TypeError, match="ctx"):
        with_agentmail(bad)


def test_with_agentmail_strips_client_and_config_from_schema() -> None:
    """LLM-visible schema should NOT include client/config."""

    from mcp.server.fastmcp import Context

    async def tool(ctx: Context, client, config, to: str, limit: int = 10):
        return to

    wrapped = with_agentmail(tool)
    import inspect

    sig = inspect.signature(wrapped)
    assert "client" not in sig.parameters
    assert "config" not in sig.parameters
    assert "ctx" not in sig.parameters
    assert "to" in sig.parameters
    assert "limit" in sig.parameters


# --- retryable coroutine check ---


def test_retryable_rejects_sync_function() -> None:
    """@retryable must only wrap async coroutine functions."""

    def sync_fn():
        return "x"

    with pytest.raises(TypeError, match="async"):
        retryable(sync_fn)


def test_retryable_wraps_async_function() -> None:
    """Sanity: the decorator returns a working coroutine function."""

    @retryable
    async def ok() -> str:
        return "ok"

    assert callable(ok)


# --- with_agentmail error wrapping ---


@pytest.mark.asyncio
async def test_with_agentmail_catches_exception_when_no_lifespan() -> None:
    """When the lifespan context is missing/wrong, returns a JSON error."""

    from mcp.server.fastmcp import Context

    @with_agentmail
    async def tool(ctx: Context, client, config):
        return "should not reach here"

    class FakeRequestContext:
        lifespan_context = "not-a-lifespan"  # wrong type

    class FakeCtx:
        request_context = FakeRequestContext()

    result = await tool(FakeCtx())
    import json

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert "Lifespan context" in parsed["message"]
