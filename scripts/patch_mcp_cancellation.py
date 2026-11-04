"""Apply the qualified MCP 1.30.0 cancellation race repair at image build time."""

import importlib.metadata
from pathlib import Path

import mcp.shared.session


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError("Unsupported dependency source; preserve the original image")
    return source.replace(old, new, 1)


if importlib.metadata.version("mcp") != "1.30.0":
    raise RuntimeError("Only mcp 1.30.0 is qualified by this patch")

path = Path(mcp.shared.session.__file__)
source = replace_once(
    path.read_text(),
    '        assert not self._completed, "Request already responded to"',
    "        if self._completed:\n            return",
)
source = replace_once(
    source,
    "        self._cancel_scope.cancel()\n        self._completed = True",
    "        if self._completed:\n            return\n"
    "        self._cancel_scope.cancel()\n        self._completed = True",
)
source = replace_once(
    source,
    "            AssertionError: If request was already responded to",
    "            Completed requests ignore late responses and cancellation",
)
path.write_text(source)
