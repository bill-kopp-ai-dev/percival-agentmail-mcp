"""Tests for the server_lifespan (Fase 2 — HTTP client lifecycle)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from agentmail.core.api_error import ApiError

from percival_agentmail_mcp.lifespan import LifespanContext


class _FakeInboxes:
    def __init__(self, behavior):
        self._behavior = behavior

    async def get(self, inbox_id: str):
        return self._behavior(inbox_id)


class _FakeAsyncAgentMail:
    def __init__(self, behavior):
        self.inboxes = _FakeInboxes(behavior)
        self.aclose = AsyncMock()


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch):
    """Wipe AGENTMAIL_* env vars so load_config doesn't leak into tests."""
    for k in (
        "AGENTMAIL_API_KEY",
        "AGENTMAIL_INBOX_ID",
        "AGENTMAIL_MAX_RESULTS",
        "AGENTMAIL_TIMEOUT",
    ):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_lifespan_context_is_frozen_dataclass() -> None:
    from dataclasses import FrozenInstanceError

    from percival_agentmail_mcp.client import AgentMailClientWrapper
    from percival_agentmail_mcp.config import ServerConfig

    cfg = ServerConfig(api_key="am_test_12345678", inbox_id="a@b.com")
    wrapper = AgentMailClientWrapper(api_key=cfg.api_key)
    ctx = LifespanContext(client=wrapper, config=cfg)

    with pytest.raises(FrozenInstanceError):
        ctx.config = cfg  # type: ignore[misc]


@pytest.mark.asyncio
async def test_lifespan_closes_client_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: pytest.MonkeyPatch,
) -> None:
    """O aclose() deve ser chamado exatamente uma vez no shutdown."""
    from percival_agentmail_mcp import server as server_mod

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

    fake = _FakeAsyncAgentMail(lambda inbox_id: {"id": inbox_id})
    monkeypatch.setattr(
        server_mod,
        "AgentMailClientWrapper",
        lambda api_key, timeout: MagicMock(client=fake),
    )

    agen = server_mod.server_lifespan(None)
    ctx = await agen.__aenter__()
    assert isinstance(ctx, LifespanContext)
    await agen.__aexit__(None, None, None)

    fake.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_raises_runtime_error_on_api_failure(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: pytest.MonkeyPatch,
) -> None:
    """Servidor deve falhar em iniciar se a health check retornar 401/403."""
    from percival_agentmail_mcp import server as server_mod

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

    def boom(inbox_id: str):
        raise ApiError(status_code=401, body="bad key")

    fake = _FakeAsyncAgentMail(boom)
    monkeypatch.setattr(
        server_mod,
        "AgentMailClientWrapper",
        lambda api_key, timeout: MagicMock(client=fake),
    )

    agen = server_mod.server_lifespan(None)
    with pytest.raises(RuntimeError) as exc:
        await agen.__aenter__()
    assert "Cannot reach AgentMail API" in str(exc.value)
    # aclose() ainda é chamado no caminho de erro
    fake.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_retries_health_check_on_503(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: pytest.MonkeyPatch,
) -> None:
    """Regression: health check should retry transient errors (503) before giving up."""
    from percival_agentmail_mcp import server as server_mod

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

    call_count = {"n": 0}

    async def flaky_get(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ApiError(status_code=503, body="down")
        return {"id": "ok"}

    # Build the fake client so that wrapper.client.inboxes.get(...) is a real
    # AsyncMock that calls our flaky coroutine.
    fake_client = MagicMock()
    fake_client.aclose = AsyncMock()
    fake_client.inboxes = MagicMock()
    fake_client.inboxes.get = AsyncMock(side_effect=flaky_get)
    monkeypatch.setattr(
        server_mod,
        "AgentMailClientWrapper",
        lambda api_key, timeout: MagicMock(client=fake_client),
    )

    # Patch the real with_retry in the client module so the test
    # doesn't sleep for the production backoff delays.
    from percival_agentmail_mcp import client as client_mod

    async def fast_retry(fn, **_):
        for _ in range(3):
            try:
                return await fn()
            except ApiError as e:
                if e.status_code == 503:
                    continue
                raise
        return await fn()

    monkeypatch.setattr(client_mod, "with_retry", fast_retry)
    # server.py imported with_retry at module load — patch the symbol it uses
    monkeypatch.setattr(server_mod, "with_retry", fast_retry)

    agen = server_mod.server_lifespan(None)
    ctx = await agen.__aenter__()
    assert isinstance(ctx, LifespanContext)
    await agen.__aexit__(None, None, None)
    assert call_count["n"] == 3
