"""Decorators that remove boilerplate from MCP tools.

The big win is ``@with_agentmail``: instead of writing

    async def send_email(ctx, ...):
        wrapper, config = get_context(ctx).client, get_context(ctx).config
        try:
            return wrapper.format_response(...)
        except Exception as e:
            return wrapper.format_error(e)

every tool becomes

    @with_agentmail
    async def send_email(ctx, client, config, ...):
        return client.format_response(...)

with automatic error wrapping and rate-limit / retry orchestration.

The trick: FastMCP inspects the wrapped function's signature to build a
JSON schema for the LLM. We must hide ``client`` and ``config`` from the
signature so the schema only contains the LLM-visible parameters.
"""

import functools
import inspect
import json
import logging
from collections.abc import Callable
from typing import TypeVar

from mcp.server.fastmcp import Context

from percival_agentmail_mcp.client import with_retry as _with_retry
from percival_agentmail_mcp.lifespan import LifespanContext

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


_INJECTED_PARAMS = {"client", "config"}
_INJECTED_AFTER_CTX = True  # ctx is the first param, injected params follow


def _build_public_signature(fn: Callable) -> inspect.Signature:
    """Return a signature with ``ctx``, ``client`` and ``config`` stripped.

    The first parameter MUST be named ``ctx`` (FastMCP convention).
    The next parameters ``client`` and ``config`` are injected by this
    decorator. Any other parameters are LLM-visible.

    Raises:
        TypeError: if the first parameter is not named ``ctx``.
    """
    sig = inspect.signature(fn)
    params_list = list(sig.parameters.items())
    if not params_list or params_list[0][0] != "ctx":
        raise TypeError(
            f"@with_agentmail requires the first parameter to be named 'ctx', "
            f"got '{params_list[0][0] if params_list else '<none>'}' in {fn!r}"
        )
    params = [p for name, p in params_list if name not in _INJECTED_PARAMS and name != "ctx"]
    return inspect.Signature(parameters=params, return_annotation=sig.return_annotation)


def with_agentmail(fn: F) -> F:
    """Inject ``client`` and ``config`` and wrap exceptions.

    The wrapped function MUST have signature::

        async def tool(ctx: Context, client: AgentMailClientWrapper,
                       config: ServerConfig, ...) -> str

    From FastMCP's perspective, only the parameters after ``ctx`` that
    are NOT ``client`` or ``config`` are exposed to the LLM.
    """

    @functools.wraps(fn)
    async def wrapper(ctx: Context, **kwargs):
        ctx_obj = ctx.request_context.lifespan_context
        if not isinstance(ctx_obj, LifespanContext):
            return json.dumps(
                {
                    "status": "error",
                    "message": "Lifespan context is missing or wrong type.",
                },
                indent=2,
            )
        client = ctx_obj.client
        try:
            return await fn(ctx, client=client, config=ctx_obj.config, **kwargs)
        except Exception as e:
            # S5: surface the tool name + affected IDs in the error so the
            # LLM gets actionable context.
            tool_name = getattr(fn, "__name__", None)
            affected = {
                k: v
                for k, v in kwargs.items()
                if isinstance(v, (str, int)) and k in {"message_id", "thread_id", "draft_id", "inbox_id"}
            }
            return client.format_error(e, tool_name=tool_name, affected=affected)

    # Hide injected params from FastMCP's schema introspection
    wrapper.__signature__ = _build_public_signature(fn)  # type: ignore[attr-defined]
    wrapper.__wrapped__ = fn  # type: ignore[attr-defined]

    return wrapper  # type: ignore[return-value]


def retryable(fn: F) -> F:
    """Wrap a tool so its single awaited call retries with backoff.

    The decorated function must be an async coroutine function returning
    an awaitable. Tools with composed logic should call ``with_retry``
    directly inside their body instead.
    """

    if not inspect.iscoroutinefunction(fn):
        raise TypeError(f"@retryable can only wrap async (coroutine) functions, got {fn!r}")

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        return await _with_retry(lambda: fn(*args, **kwargs))

    return wrapper  # type: ignore[return-value]
