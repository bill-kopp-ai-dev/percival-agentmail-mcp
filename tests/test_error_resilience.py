"""Tests for error sanitization and resilience (Fase 3)."""

import json

import httpx
import pytest
from agentmail.core.api_error import ApiError

from percival_agentmail_mcp.client import (
    AgentMailClientWrapper,
    RateLimiter,
    with_retry,
)


@pytest.fixture
def wrapper() -> AgentMailClientWrapper:
    return AgentMailClientWrapper(api_key="am_test_12345678")


# --- format_error ---


def test_format_error_api_401_mentions_api_key(wrapper: AgentMailClientWrapper) -> None:
    err = ApiError(status_code=401, body="bad key")
    parsed = json.loads(wrapper.format_error(err))
    assert parsed["code"] == 401
    assert "AGENTMAIL_API_KEY" in parsed["message"]


def test_format_error_api_429_suggests_retry(wrapper: AgentMailClientWrapper) -> None:
    err = ApiError(status_code=429, body="slow down")
    parsed = json.loads(wrapper.format_error(err))
    msg = parsed["message"].lower()
    # 429 is retryable — the hint mentions retries or wait.
    assert ("transient" in msg) or ("retries" in msg) or ("wait" in msg)


def test_format_error_api_500(wrapper: AgentMailClientWrapper) -> None:
    err = ApiError(status_code=500, body="boom")
    parsed = json.loads(wrapper.format_error(err))
    assert parsed["code"] == 500
    # 500 is retryable — the hint now mentions the server has already
    # exhausted internal retries and asks the caller to wait.
    msg = parsed["message"].lower()
    assert ("transient" in msg) or ("retries" in msg) or ("wait" in msg)


def test_format_error_api_unknown_status(wrapper: AgentMailClientWrapper) -> None:
    err = ApiError(status_code=599, body="?")
    parsed = json.loads(wrapper.format_error(err))
    assert "599" in parsed["message"]


def test_format_error_api_with_none_status_code(wrapper: AgentMailClientWrapper) -> None:
    """Regression: status_code=None must not produce 'HTTP None' or 'code: null'."""
    err = ApiError(status_code=None, body="unparseable")
    parsed = json.loads(wrapper.format_error(err))
    assert parsed["status"] == "error"
    assert parsed["code"] == "UNKNOWN"
    assert "HTTP None" not in parsed["message"]
    assert "None" not in parsed["message"]


def test_serialize_handles_bytes(wrapper: AgentMailClientWrapper) -> None:
    """Regression: bytes in the response would crash json.dumps."""
    out = wrapper.format_response({"data": b"binary", "text": "ok"})
    parsed = json.loads(out)
    assert parsed["text"] == "ok"
    assert "base64" in parsed["data"]


def test_serialize_handles_set(wrapper: AgentMailClientWrapper) -> None:
    """Regression: sets in the response would crash json.dumps."""
    out = wrapper.format_response({"tags": {"urgent", "work"}})
    parsed = json.loads(out)
    assert isinstance(parsed["tags"], list)
    assert set(parsed["tags"]) == {"urgent", "work"}


def test_serialize_handles_tuple(wrapper: AgentMailClientWrapper) -> None:
    """Tuples should become lists."""
    out = wrapper.format_response({"items": ("a", "b", "c")})
    parsed = json.loads(out)
    assert parsed["items"] == ["a", "b", "c"]


def test_with_retry_skips_when_status_none(wrapper: AgentMailClientWrapper) -> None:
    """Regression: ApiError with status_code=None must NOT be retried."""
    import asyncio

    async def boom() -> None:
        raise ApiError(status_code=None, body="?")

    with pytest.raises(ApiError):
        asyncio.run(with_retry(boom, base_delay=0.001))


def test_format_error_httpx_timeout(wrapper: AgentMailClientWrapper) -> None:
    err = httpx.ReadTimeout("read timed out")
    parsed = json.loads(wrapper.format_error(err))
    assert parsed["code"] == "TIMEOUT"


def test_format_error_httpx_connect(wrapper: AgentMailClientWrapper) -> None:
    err = httpx.ConnectError("name resolution failed")
    parsed = json.loads(wrapper.format_error(err))
    assert parsed["code"] == "CONNECTION"


def test_format_error_pydantic_validation(wrapper: AgentMailClientWrapper) -> None:
    from pydantic import BaseModel, ValidationError

    class M(BaseModel):
        x: int

    try:
        M(x="not an int")  # type: ignore[arg-type]
    except ValidationError as e:
        parsed = json.loads(wrapper.format_error(e))

    assert parsed["code"] == "VALIDATION"
    assert "x" in parsed["message"]


def test_format_error_unexpected_does_not_leak_path(wrapper: AgentMailClientWrapper) -> None:
    err = RuntimeError("/home/user/.secret leaked")
    parsed = json.loads(wrapper.format_error(err))
    assert "/home/user" not in parsed["message"]


# --- with_retry ---


@pytest.mark.asyncio
async def test_with_retry_succeeds_after_429() -> None:
    attempt = {"n": 0}

    async def flaky() -> str:
        attempt["n"] += 1
        if attempt["n"] < 3:
            raise ApiError(status_code=429, body="slow")
        return "ok"

    result = await with_retry(flaky, base_delay=0.001, max_delay=0.01)
    assert result == "ok"
    assert attempt["n"] == 3


@pytest.mark.asyncio
async def test_with_retry_succeeds_after_503() -> None:
    attempt = {"n": 0}

    async def flaky() -> str:
        attempt["n"] += 1
        if attempt["n"] < 2:
            raise ApiError(status_code=503, body="down")
        return "ok"

    result = await with_retry(flaky, base_delay=0.001, max_delay=0.01)
    assert result == "ok"
    assert attempt["n"] == 2


@pytest.mark.asyncio
async def test_with_retry_does_not_retry_404() -> None:
    attempt = {"n": 0}

    async def notfound() -> None:
        attempt["n"] += 1
        raise ApiError(status_code=404, body="missing")

    with pytest.raises(ApiError):
        await with_retry(notfound, base_delay=0.001)
    assert attempt["n"] == 1


@pytest.mark.asyncio
async def test_with_retry_does_not_retry_422() -> None:
    attempt = {"n": 0}

    async def badreq() -> None:
        attempt["n"] += 1
        raise ApiError(status_code=422, body="invalid")

    with pytest.raises(ApiError):
        await with_retry(badreq, base_delay=0.001)
    assert attempt["n"] == 1


@pytest.mark.asyncio
async def test_with_retry_retries_timeout_then_gives_up() -> None:
    attempt = {"n": 0}

    async def always_timeout() -> None:
        attempt["n"] += 1
        raise httpx.ReadTimeout("x")

    with pytest.raises(httpx.ReadTimeout):
        await with_retry(always_timeout, max_attempts=3, base_delay=0.001)
    assert attempt["n"] == 3


# --- RateLimiter ---


def test_rate_limiter_allows_within_window() -> None:
    rl = RateLimiter(max_calls=3, window_seconds=10.0)
    for _ in range(3):
        rl.acquire()


def test_rate_limiter_blocks_after_max_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    rl = RateLimiter(max_calls=2, window_seconds=0.5)
    rl.acquire()
    rl.acquire()
    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    rl.acquire()
    assert sleeps and sleeps[0] > 0
