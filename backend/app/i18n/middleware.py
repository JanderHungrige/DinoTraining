"""German answers for German readers, on the way out (doc 113).

For a request whose `Accept-Language` starts with ``de``, a JSON response under the API
prefix is read, its **text fields** translated (`translate.py`), and sent on with a fixed
`Content-Length`. Everything else passes through untouched: other languages, no header
(MCP's internal calls send none, so assistants read English), streaming responses such as
server-sent events, and anything that is not JSON.

Only text fields are translated. Ids, paths, keys, targets, names, class names and phrases
are the user's own words or machine identifiers; translating one would break the client
that sends it back, or rename what the user named.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.i18n.translate import translate_text

logger = logging.getLogger(__name__)

#: Keys whose string values (or lists of strings) are prose written for a person.
TEXT_FIELDS = frozenset(
    {
        "title",
        "what",
        "why",
        "action",
        "help",
        "label",
        "term",
        "summary",
        "message",
        "detail",
        "fix",
        "data_format",
        "minimums_why",
        "what_trains",
        "image_sizes",
        "unavailable_reason",
        "gates",
        "notes",
        "adapter_notes",
        "warnings",
        "reason",
        "open_problems",
        "explained",
        "fit_explained",
        "normalisation",
        "masks",
        "covers",
    }
)


def wants_german(headers: Headers) -> bool:
    return headers.get("accept-language", "").strip().lower().startswith("de")


def translate_body(value: Any, lang: str, key: str | None = None) -> Any:
    """`value` with every text field's strings translated; everything else as it was."""
    if isinstance(value, dict):
        return {k: translate_body(v, lang, k) for k, v in value.items()}
    if isinstance(value, list):
        return [translate_body(item, lang, key) for item in value]
    if isinstance(value, str) and key in TEXT_FIELDS:
        return translate_text(value, lang)
    return value


def _is_json(headers: Headers) -> bool:
    return headers.get("content-type", "").split(";")[0].strip().lower() == "application/json"


class GermanTextMiddleware:
    """Pure ASGI, so a streaming response is never buffered: only JSON is held back."""

    def __init__(self, app: ASGIApp, prefix: str = "/api/v1") -> None:
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or not str(scope.get("path", "")).startswith(self.prefix)
            or not wants_german(Headers(scope=scope))
        ):
            await self.app(scope, receive, send)
            return
        await self.app(scope, receive, _Translating(scope, send).send)


class _Translating:
    """One response's `send`: holds a JSON body back until it is complete, then translates."""

    def __init__(self, scope: Scope, send: Send) -> None:
        self.scope = scope
        self.downstream = send
        self.start: Message | None = None
        self.passthrough = False
        self.chunks: list[bytes] = []

    async def send(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            if _is_json(Headers(raw=message["headers"])):
                self.start = message
                return
            self.passthrough = True
        if self.passthrough or message["type"] != "http.response.body" or self.start is None:
            await self.downstream(message)
            return
        self.chunks.append(message.get("body", b""))
        if message.get("more_body", False):
            return
        await self._flush(b"".join(self.chunks))

    async def _flush(self, body: bytes) -> None:
        assert self.start is not None
        translated = self._translate(body)
        headers = MutableHeaders(raw=list(self.start["headers"]))
        headers["content-length"] = str(len(translated))
        headers.add_vary_header("Accept-Language")
        await self.downstream({**self.start, "headers": headers.raw})
        await self.downstream({"type": "http.response.body", "body": translated})

    def _translate(self, body: bytes) -> bytes:
        if not body:
            return body
        try:
            parsed = json.loads(body)
        except ValueError as error:
            # Sent on in English rather than failing the response; logged so it is seen.
            logger.warning(
                "Left an unparseable JSON response to %s in English: %s",
                self.scope.get("path"),
                error,
            )
            return body
        translated = translate_body(parsed, "de")
        return json.dumps(translated, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


__all__ = ["TEXT_FIELDS", "GermanTextMiddleware", "translate_body", "wants_german"]
