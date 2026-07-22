"""Regression: AgentMailClientWrapper.aclose() must close the underlying httpx client.

Discovered live on 2026-07-22: when the lifespan context was closed, our
``server_lifespan`` called ``wrapper.client.aclose()`` and crashed with
``AttributeError: 'AsyncAgentMail' object has no attribute 'aclose'``.
The SDK holds its httpx client at
``wrapper.client._client_wrapper.httpx_client`` and exposes no public
``aclose()``. ``AgentMailClientWrapper.aclose`` was added so the
lifespan can close connections cleanly without leaking.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from percival_agentmail_mcp.client import AgentMailClientWrapper


@pytest.mark.asyncio
async def test_wrapper_aclose_calls_underlying_httpx_client() -> None:
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    # Stub the nested SDK chain
    fake_httpx = MagicMock()
    fake_httpx.aclose = AsyncMock()
    wrapper.client = MagicMock()
    wrapper.client._client_wrapper = MagicMock(httpx_client=fake_httpx)

    await wrapper.aclose()

    fake_httpx.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_wrapper_aclose_no_ops_when_sdk_structure_changes() -> None:
    """If the SDK shape changes in a future release, aclose() must be a no-op
    rather than raise — so the lifespan shutdown never blocks the server.
    """
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    wrapper.client = MagicMock(spec=[])  # no _client_wrapper attribute
    # No exception is good enough.
    await wrapper.aclose()


@pytest.mark.asyncio
async def test_server_lifespan_aclose_path_passes(monkeypatch, isolated_env) -> None:
    """End-to-end: server_lifespan does NOT raise on shutdown."""
    from percival_agentmail_mcp import server as server_mod

    fake_wrapper = MagicMock()
    fake_wrapper.client = MagicMock()
    fake_wrapper.client.inboxes.get = AsyncMock(return_value={"id": "ok"})
    fake_wrapper.aclose = AsyncMock()

    async def fast_retry(fn, **_):
        return await fn()

    monkeypatch.setattr(
        server_mod,
        "load_config",
        lambda: MagicMock(
            api_key="am_test_12345678",
            inbox_id="agent@agentmail.to",
            max_results=25,
            timeout=30,
        ),
    )
    monkeypatch.setattr(server_mod, "with_retry", fast_retry)
    monkeypatch.setattr(server_mod, "AgentMailClientWrapper", lambda api_key, timeout: fake_wrapper)

    agen = server_mod.server_lifespan(None)
    await agen.__aenter__()
    await agen.__aexit__(None, None, None)
    fake_wrapper.aclose.assert_awaited_once()
