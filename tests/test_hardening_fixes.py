"""Regression tests for the review-time hardening pass.

Each test here was added together with the corresponding fix. Keep the
test name and the source-code location in sync so future readers can
trace back why each helper exists.
"""

import asyncio
import json

import pytest

from percival_agentmail_mcp.constants import SYSTEM_LABELS
from percival_agentmail_mcp.helpers import (
    assert_no_system_labels,
    assert_non_empty,
    cap_limit,
)

# ---------------------------------------------------------------------------
# assert_no_system_labels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "labels",
    [
        None,
        [],
        ["mcp-sent"],
        ["important", "urgent"],
        ["custom-foo"],
    ],
)
def test_assert_no_system_labels_allows_safe(labels) -> None:
    """Safe label sets pass through without raising."""
    assert_no_system_labels(labels, field="add_labels", tool="mail_test")


@pytest.mark.parametrize(
    "labels,expected_in_message",
    [
        (["sent"], "'sent'"),
        (["read"], "'read'"),
        (["unread", "draft"], "'unread'"),
        (["important", "received", "urgent"], "'received'"),
    ],
)
def test_assert_no_system_labels_blocks_system(labels, expected_in_message) -> None:
    """Reserved system labels raise with a hint that names the offending label."""
    with pytest.raises(ValueError) as exc:
        assert_no_system_labels(labels, field="add_labels", tool="mail_test")
    msg = str(exc.value)
    assert expected_in_message in msg
    assert "Cannot use system label" in msg
    assert "mail_test" in msg  # tool name embedded for LLM context
    assert "add_labels" in msg  # field name embedded for LLM context


def test_assert_no_system_labels_includes_tool_name() -> None:
    """The tool name surfaces in the error so the LLM can attribute it."""
    with pytest.raises(ValueError) as exc:
        assert_no_system_labels(["sent"], field="add_labels", tool="mail_send_draft")
    assert "mail_send_draft" in str(exc.value)


def test_system_labels_constant_is_complete() -> None:
    """The blocklist covers every label the upstream explicitly rejects."""
    assert {"sent", "received", "unread", "draft", "read"} <= SYSTEM_LABELS


# ---------------------------------------------------------------------------
# assert_non_empty
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["a@example.com", ["a@example.com"], ["a@example.com", "b@example.com"]],
)
def test_assert_non_empty_accepts_valid(value) -> None:
    assert_non_empty(value, field="to")


@pytest.mark.parametrize(
    "value",
    [None, "", "   ", [], ["   ", ""], 0, False],
)
def test_assert_non_empty_rejects_empty(value) -> None:
    with pytest.raises(ValueError) as exc:
        assert_non_empty(value, field="to")
    assert "to" in str(exc.value)


def test_assert_non_empty_rejects_non_collection() -> None:
    """A scalar that is not a known empty value still raises."""
    with pytest.raises(ValueError):
        assert_non_empty(42, field="to")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# cap_limit
# ---------------------------------------------------------------------------


def test_cap_limit_clamps_to_hard_cap() -> None:
    assert cap_limit(99999, default=25, hard_cap=50) == 50


def test_cap_limit_falls_back_to_default_for_invalid_int() -> None:
    """Regression: a non-int limit (e.g. an LLM passing "ten") must NOT
    raise ``TypeError`` from the ``limit < 1`` comparison; it must fall
    back to the default.
    """
    assert cap_limit("ten", default=25, hard_cap=50) == 25


def test_cap_limit_falls_back_to_default_for_none() -> None:
    assert cap_limit(None, default=25, hard_cap=50) == 25


def test_cap_limit_falls_back_to_default_for_zero() -> None:
    assert cap_limit(0, default=25, hard_cap=50) == 25


def test_cap_limit_passes_through_in_range_int() -> None:
    assert cap_limit(10, default=25, hard_cap=50) == 10


# ---------------------------------------------------------------------------
# Async rate limiter — event-loop non-blocking regression
# ---------------------------------------------------------------------------


def test_format_response_is_coroutine_function() -> None:
    """``format_response`` must be async so callers can ``await`` it.

    This was the cheap insurance against regressing the
    ``time.sleep`` → ``asyncio.sleep`` fix: if anyone reverts it to a
    sync function, FastMCP would surface a warning and the tool handlers
    would silently produce no rate-limit protection.
    """
    import inspect

    from percival_agentmail_mcp.client import AgentMailClientWrapper

    assert inspect.iscoroutinefunction(AgentMailClientWrapper.format_response)
    assert inspect.iscoroutinefunction(AgentMailClientWrapper.format_fenced)


@pytest.mark.asyncio
async def test_format_response_uses_async_rate_limiter() -> None:
    """Regression: ``format_response`` must ``await`` the rate limiter.

    If the limiter were still sync (and still called ``time.sleep``),
    the entire asyncio loop would be blocked whenever the window was
    full — exactly the denial-of-service the async refactor prevents.
    """
    from percival_agentmail_mcp.client import AgentMailClientWrapper

    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    # Replace the limiter so the test does not sleep for the real
    # window — we only care that ``format_response`` reaches it.
    wrapper._limiter = _CountingLimiter()

    await wrapper.format_response({"id": "x"})
    assert wrapper._limiter.acquired == 1
    await wrapper.format_response({"id": "y"})
    assert wrapper._limiter.acquired == 2


class _CountingLimiter:
    """Minimal stand-in for ``RateLimiter`` used by the async-refactor
    regression: records every ``acquire()`` call without ever sleeping.
    """

    def __init__(self) -> None:
        self.acquired = 0

    async def acquire(self) -> None:
        self.acquired += 1


# ---------------------------------------------------------------------------
# format_error truncation indicator
# ---------------------------------------------------------------------------


def test_format_error_appends_ellipsis_when_upstream_truncated() -> None:
    """Regression: ``Upstream: ...`` must end with "…" when the joined
    upstream details exceed the 600-char cap, so the LLM knows the text
    is incomplete instead of assuming a full sentence.
    """
    from agentmail.core.api_error import ApiError

    from percival_agentmail_mcp.client import AgentMailClientWrapper

    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    # Build a giant body that exceeds 600 chars after joining
    long_text = "x" * 800
    api_err = ApiError(status_code=400, body=long_text)
    out = json.loads(wrapper.format_error(api_err))
    assert "Upstream:" in out["message"]
    assert out["message"].rstrip().endswith("…")


def test_format_error_no_ellipsis_when_under_cap() -> None:
    """Regression: short upstream messages must NOT have a spurious "…"."""
    from agentmail.core.api_error import ApiError

    from percival_agentmail_mcp.client import AgentMailClientWrapper

    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    api_err = ApiError(status_code=400, body="short upstream message")
    out = json.loads(wrapper.format_error(api_err))
    assert "Upstream: short upstream message" in out["message"]
    assert not out["message"].rstrip().endswith("…")
