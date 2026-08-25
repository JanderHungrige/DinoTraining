"""The endpoint reference, rendered from the live OpenAPI schema (doc 63).

**Generated, never transcribed.** A hand-maintained endpoint list is wrong the first time
anyone adds a route, and a confidently wrong list is worse than no list — a reader has no
way to tell which half to trust. Adding a route to `router.py` puts it in the guide with no
other edit, which is the only way that stays true.

What is *not* generated is the order to call things in. That is `workflows.py`, and it is
prose because no schema records it.
"""

from __future__ import annotations

from typing import Any

#: Methods worth listing, in the order a reader scans for them.
_METHODS = ("get", "post", "put", "patch", "delete")


def render_reference(openapi: dict[str, Any]) -> str:
    """Every operation, grouped by tag, as markdown.

    Grouped by tag rather than by path because that is how the API is *organised* — the
    router assigns them — and an alphabetical path list buries `POST /training/jobs` between
    two dataset routes.
    """
    groups: dict[str, list[str]] = {}

    for path, operations in sorted(openapi.get("paths", {}).items()):
        for method in _METHODS:
            operation = operations.get(method)
            if not isinstance(operation, dict):
                continue
            tag = (operation.get("tags") or ["other"])[0]
            groups.setdefault(tag, []).append(_render_operation(method, path, operation))

    lines = [
        "## Endpoint reference",
        "",
        "Generated from this backend's own OpenAPI schema, so it describes the version you "
        "are talking to. The full schema, with every request and response field typed, is "
        "at `/openapi.json`; interactive docs are at `/docs`.",
        "",
    ]
    for tag in sorted(groups):
        lines.append(f"### {tag}")
        lines.append("")
        lines.extend(groups[tag])
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_operation(method: str, path: str, operation: dict[str, Any]) -> str:
    """One line per operation: what to call, and what it is for."""
    summary = str(operation.get("summary") or "").strip()
    required = _required_fields(operation)
    parts = [f"- `{method.upper()} {path}`"]
    if summary:
        parts.append(f" — {summary}")
    if required:
        # The required fields, and only those: an agent reading a reference wants to know
        # what it cannot omit. Everything else is in the schema it can fetch.
        parts.append(f" *(requires: {', '.join(required)})*")
    return "".join(parts)


def _required_fields(operation: dict[str, Any]) -> list[str]:
    """Required body fields, from the inlined request schema where there is one.

    Best effort by design. A `$ref` is not resolved here — following references would make
    this a schema walker, and the one place that already does that correctly is
    `/openapi.json` itself, which the guide points at.
    """
    body = operation.get("requestBody")
    if not isinstance(body, dict):
        return []
    content = body.get("content")
    if not isinstance(content, dict):
        return []
    schema = content.get("application/json", {}).get("schema")
    if not isinstance(schema, dict):
        return []
    required = schema.get("required")
    return [str(name) for name in required] if isinstance(required, list) else []


__all__ = ["render_reference"]
