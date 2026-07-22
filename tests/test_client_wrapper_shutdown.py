"""Regression: AgentMailClientWrapper.aclose() must close the underlying httpx client.

Discovered live on 2026-07-22: when the lifespan context was closed, our
``server_lifespan`` called ``wrapper.client.aclose()`` and crashed with
``AttributeError: 'AsyncAgentMail' object has no attribute 'aclose'``.
The SDK holds its real ``httpx.AsyncClient`` two levels deep, at
``wrapper.client._client_wrapper.httpx_client.httpx_client`` — the
first ``.httpx_client`` is agentmail's own ``AsyncHttpClient`` wrapper,
which has no ``aclose()`` of its own. A first attempt at this fix
stopped one level too shallow and silently no-op'd (verified against
the live agentmail-sdk 0.5.x object graph), leaking the connection
without raising. ``AgentMailClientWrapper.aclose`` now walks the full
chain so the lifespan can close connections cleanly without leaking.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from percival_agentmail_mcp.client import AgentMailClientWrapper


@pytest.mark.asyncio
async def test_wrapper_aclose_calls_underlying_httpx_client() -> None:
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    # Stub the nested SDK chain: _client_wrapper.httpx_client is agentmail's
    # own AsyncHttpClient; ITS .httpx_client is the real httpx.AsyncClient.
    real_httpx_client = MagicMock()
    real_httpx_client.aclose = AsyncMock()
    agentmail_http_client = MagicMock(httpx_client=real_httpx_client)
    wrapper.client = MagicMock()
    wrapper.client._client_wrapper = MagicMock(httpx_client=agentmail_http_client)

    await wrapper.aclose()

    real_httpx_client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_wrapper_aclose_no_ops_when_intermediate_wrapper_lacks_httpx_client() -> None:
    """Regression: a fix that stops one level too shallow (closing
    agentmail's own AsyncHttpClient, which has no aclose()) must not
    raise — but this test also guards against silently "fixing" nothing
    by asserting the real client's aclose is what actually gets called
    in the happy path above. Here we only check the no-op is safe when
    the intermediate object has no further nesting.
    """
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    agentmail_http_client = MagicMock(spec=[])  # no nested .httpx_client
    wrapper.client = MagicMock()
    wrapper.client._client_wrapper = MagicMock(httpx_client=agentmail_http_client)

    await wrapper.aclose()  # must not raise


@pytest.mark.asyncio
async def test_wrapper_aclose_closes_the_real_sdk_httpx_client() -> None:
    """No mocks: exercises the actual agentmail-sdk object graph.

    This is the test that would have caught both the original crash
    (``AttributeError``) and the follow-up silent no-op (closing the
    wrong nesting level) — mock-based tests kept passing in both cases
    because the mock shape didn't match the SDK's real structure.
    """
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    real_httpx_client = wrapper.client._client_wrapper.httpx_client.httpx_client

    assert real_httpx_client.is_closed is False
    await wrapper.aclose()
    assert real_httpx_client.is_closed is True


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
