"""Internal helpers for argument normalization and kwarg building.

Pure functions; easy to unit-test.
"""

import json
from typing import Any


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
    """Clamp a user-supplied limit into ``[1, hard_cap]``."""
    if not limit or limit < 1:
        return min(default, hard_cap)
    return min(limit, hard_cap)


def build_kwargs(base: dict[str, Any], optional: dict[str, Any]) -> dict[str, Any]:
    """Return ``base`` plus only the ``optional`` entries whose value is not None."""
    return {**base, **{k: v for k, v in optional.items() if v is not None}}
