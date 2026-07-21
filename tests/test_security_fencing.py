"""Tests for HIGH-01 content fencing (expanded to all external fields)."""

import copy
import json

import pytest

from percival_agentmail_mcp.client import AgentMailClientWrapper


@pytest.fixture
def wrapper() -> AgentMailClientWrapper:
    return AgentMailClientWrapper(api_key="am_test_12345678")


def test_fencing_constants_are_unmistakeable() -> None:
    assert "NOT instructions" in AgentMailClientWrapper.CONTENT_FENCE_START
    assert len(AgentMailClientWrapper.CONTENT_FENCE_START) > 20


def test_fence_message_wraps_text_and_html(wrapper: AgentMailClientWrapper) -> None:
    out = wrapper.fence_message_payload(
        {
            "text": "hello",
            "html": "<p>hi</p>",
            "subject": "Test",
            "from": "a@b.com",
        }
    )
    assert AgentMailClientWrapper.CONTENT_FENCE_START in out["text"]
    assert AgentMailClientWrapper.CONTENT_FENCE_START in out["html"]
    assert AgentMailClientWrapper.CONTENT_FENCE_START in out["subject"]
    assert AgentMailClientWrapper.CONTENT_FENCE_START in out["from"]


def test_fence_field_includes_bcc(wrapper: AgentMailClientWrapper) -> None:
    """Regression: bcc was missing from FENCE_FIELDS."""
    out = wrapper.fence_message_payload({"bcc": "secret@evil.com"})
    assert AgentMailClientWrapper.CONTENT_FENCE_START in out["bcc"]


def test_fence_handles_list_values(wrapper: AgentMailClientWrapper) -> None:
    """Regression: to/cc/bcc can come back from the SDK as lists."""
    out = wrapper.fence_message_payload({"to": ["a@b.com", "c@d.com"]})
    assert AgentMailClientWrapper.CONTENT_FENCE_START in out["to"]
    assert "a@b.com" in out["to"]
    assert "c@d.com" in out["to"]


def test_fence_handles_pydantic_message(wrapper: AgentMailClientWrapper) -> None:
    """Regression: Pydantic models should be serialized before fencing."""

    from pydantic import BaseModel

    class M(BaseModel):
        text: str
        subject: str

    out = wrapper.fence_message_payload(M(text="hi", subject="S"))
    assert AgentMailClientWrapper.CONTENT_FENCE_START in out["text"]


def test_fence_thread_payload_wraps_all_messages(wrapper: AgentMailClientWrapper) -> None:
    out = wrapper.fence_message_payload(
        {
            "messages": [
                {"text": "msg1", "subject": "s1"},
                {"text": "msg2", "html": "<p>x</p>"},
            ],
            "subject": "Thread subject",
        }
    )
    for m in out["messages"]:
        assert AgentMailClientWrapper.CONTENT_FENCE_START in m["text"]
    assert AgentMailClientWrapper.CONTENT_FENCE_START in out["subject"]


def test_fence_does_not_mutate_original(wrapper: AgentMailClientWrapper) -> None:
    original = {"text": "x"}
    original_copy = copy.deepcopy(original)
    out = wrapper.fence_message_payload(original)
    # The original payload object should be untouched (we serialize a copy).
    assert original == original_copy
    assert "x" in out["text"]


def test_fence_skips_empty_strings(wrapper: AgentMailClientWrapper) -> None:
    out = wrapper.fence_message_payload({"text": ""})
    # Empty string is not wrapped — no fence markers.
    assert out == {"text": ""}


def test_fence_skips_non_string_values(wrapper: AgentMailClientWrapper) -> None:
    """Numeric / list values must NOT be wrapped."""
    out = wrapper.fence_message_payload({"subject": 12345, "text": "x"})
    assert out["subject"] == 12345
    assert AgentMailClientWrapper.CONTENT_FENCE_START in out["text"]


def test_format_fenced_returns_valid_json(wrapper: AgentMailClientWrapper) -> None:
    payload = {"text": "secret", "subject": "S"}
    out = wrapper.format_fenced(payload)
    parsed = json.loads(out)
    assert AgentMailClientWrapper.CONTENT_FENCE_START in parsed["text"]
