"""Internal helpers for argument normalization and kwarg building.

Pure functions; easy to unit-test.
"""

import json
from typing import Any

from percival_agentmail_mcp.constants import SYSTEM_LABELS


def normalize_list(val: Any) -> list[str] | None:
    """Flexibly coerce list / CSV / JSON-string inputs into a list of strings.

    Returns ``None`` for ``None`` input. Returns an empty list for an
    empty / whitespace-only string. Otherwise:

    - ``"[1, 2, 3]"`` (JSON list) → parsed list of strings
    - ``"a, b, c"`` (CSV) → ``["a", "b", "c"]``
    - ``["a", "b"]`` → ``["a", "b"]`` (coerced to str)
    - anything else → wrapped in a list and stringified.

    If the value looks like a JSON list (``[...``) but the JSON is
    malformed, the original string is preserved as a single-element list
    rather than silently split on commas, so the LLM gets actionable
    feedback.
    """
    if val is None:
        return None
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return []
        if val.startswith("["):
            # Try to parse as JSON list, but only if it is balanced
            if val.endswith("]"):
                try:
                    parsed = json.loads(val)
                except json.JSONDecodeError:
                    # Malformed JSON list — keep as a single string so the
                    # caller can see the bad input instead of getting a
                    # silently split version.
                    return [val]
                if isinstance(parsed, list):
                    return [str(i) for i in parsed]
                # JSON parsed but not a list (e.g., an object)
                return [val]
            # Starts with '[' but no closing ']' — keep as a single string.
            return [val]
        return [s.strip() for s in val.split(",") if s.strip()]
    if isinstance(val, list):
        return [str(i) for i in val]
    return [str(val)]


def cap_limit(limit: int | None, default: int, hard_cap: int) -> int:
    """Clamp a user-supplied limit into ``[1, hard_cap]``.

    Defensive: if ``limit`` is not an int (e.g. an LLM passed a string
    via a JSON-RPC number-coercion gap), fall back to ``default``
    instead of raising ``TypeError`` from the ``limit < 1`` comparison.
    """
    if not isinstance(limit, int) or limit < 1:
        return min(default, hard_cap)
    return min(limit, hard_cap)


def build_kwargs(base: dict[str, Any], optional: dict[str, Any]) -> dict[str, Any]:
    """Return ``base`` plus only the ``optional`` entries whose value is not None."""
    return {**base, **{k: v for k, v in optional.items() if v is not None}}


def assert_no_system_labels(
    labels: list[str] | None,
    *,
    field: str,
    tool: str | None = None,
) -> None:
    """Raise ``ValueError`` if any of ``labels`` is a reserved system label.

    The AgentMail upstream rejects add/remove on system labels ("sent",
    "received", "unread", "draft", "read") with HTTP 400 "Cannot use
    system label". Rather than letting the LLM round-trip that 400, we
    surface a clear error envelope up front that names the offending
    label(s) and hints at the custom-label sentinel to use instead.

    Args:
        labels: Already-normalized list of label strings (or None).
        field: Argument name being validated, e.g. ``"add_labels"``.
        tool: Optional tool name to embed in the message; helps the LLM
            attribute the error correctly when several tools share the
            same helper.

    Raises:
        ValueError: when at least one entry is a reserved system label.
    """
    if not labels:
        return
    blocked = [label for label in labels if label in SYSTEM_LABELS]
    if not blocked:
        return
    names = ", ".join(f"'{label}'" for label in blocked)
    tool_hint = f" by {tool}" if tool else ""
    raise ValueError(
        f"{field} contains system label(s) {names}{tool_hint}, which the "
        f"AgentMail upstream rejects with HTTP 400 'Cannot use system "
        f"label'. Use a custom label (prefix 'mcp-' to avoid collisions) "
        f"instead, or call mail_mark_thread_read for the read flag."
    )


def assert_non_empty(value: Any, *, field: str) -> None:
    """Raise ``ValueError`` when ``value`` is ``None``, an empty string,
    an empty list, or a list of empty/whitespace-only strings.

    Used by send tools so an LLM doesn't accidentally invoke
    ``mail_send_email`` with ``to=[]`` (which the upstream may accept and
    send to nobody) or ``mail_send_draft`` with no recipients.
    """
    if value is None:
        raise ValueError(f"{field} is required and must be a non-empty list of recipients.")
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(f"{field} must be a non-empty list of recipients (got empty string).")
        return
    if isinstance(value, list):
        if not value:
            raise ValueError(f"{field} must be a non-empty list of recipients (got empty list).")
        if all(isinstance(v, str) and not v.strip() for v in value):
            raise ValueError(f"{field} contains only empty/whitespace strings.")
        return
    raise ValueError(f"{field} must be a list of recipient strings (got {type(value).__name__}).")
