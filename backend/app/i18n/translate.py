"""English text in, German text out, by template (doc 113).

The backend writes English; this module translates an answer on its way out, so the code,
the MCP tools and the stored audits stay English (doc 113's decision).

A catalogue entry is the English text beside its German. Where the English varies, the
entry is a **template**: ``"Only {count} images"`` → ``"Nur {count} Bilder"``. The captured
values (numbers, class names, paths) go into the German unchanged. Placeholders:

* ``{name}`` — a value, kept as it is; never spans two sentences.
* ``{#name}`` — a number, kept as it is.
* ``{+name}`` — English prose inside the sentence (a model's label, "boxes"): translated too,
  first from the catalogue's *fragments* (words only safe to translate inside a sentence),
  then like any text.
* ``{*name}`` — like ``{+name}``, but may span sentences (a reason assembled elsewhere).

A text assembled from sentences the catalogue knows one by one (a refusal listing its failed
checks) is translated sentence by sentence. Unmatched text passes through unchanged: never
an error, never an empty string.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from types import ModuleType

from app.i18n import (
    de_audit,
    de_audit_task,
    de_cloud,
    de_errors,
    de_jobs,
    de_parameters,
    de_parameters_sam,
    de_prep,
    de_requirements,
    de_targets,
)

MODULES: tuple[ModuleType, ...] = (
    de_audit,
    de_audit_task,
    de_cloud,
    de_errors,
    de_jobs,
    de_parameters,
    de_parameters_sam,
    de_prep,
    de_requirements,
    de_targets,
)
_PLACEHOLDER = re.compile(r"\{([+#*]?)([a-z_][a-z0-9_]*)\}")
#: Where one sentence ends and the next begins.
_BOUNDARY = r"[.!?…]\s+(?=[A-Z'\"(„])"
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-Z'\"(„])")
_CAPTURE = {
    "": rf"(?:(?!{_BOUNDARY})[\s\S])+?",
    "+": rf"(?:(?!{_BOUNDARY})[\s\S])+?",
    "#": r"[-+]?\d+(?:[.,]\d+)?",
    "*": r"[\s\S]+?",
}
#: Templates are bucketed by the first characters of their literal start.
_PREFIX = 3
#: How deep translation may recurse: a reason inside a finding inside a refusal.
_MAX_DEPTH = 8


@dataclass(frozen=True)
class Template:
    english: str
    german: str
    pattern: re.Pattern[str]
    #: Placeholder names whose captured value is translated as well.
    recursive: frozenset[str]

    def fill(self, match: re.Match[str], depth: int) -> str:
        def value(found: re.Match[str]) -> str:
            name = found.group(2)
            captured = match.group(name)
            if name in self.recursive:
                return _translate(captured, depth + 1, fragment=True)
            return captured

        return _PLACEHOLDER.sub(value, self.german)


def compile_template(english: str, german: str) -> Template:
    """An anchored regex from the English template; each placeholder a non-greedy group."""
    parts: list[str] = []
    recursive: set[str] = set()
    names: set[str] = set()
    position = 0
    for found in _PLACEHOLDER.finditer(english):
        parts.append(re.escape(english[position : found.start()]))
        kind, name = found.group(1), found.group(2)
        parts.append(f"(?P={name})" if name in names else f"(?P<{name}>{_CAPTURE[kind]})")
        names.add(name)
        if kind in {"+", "*"}:
            recursive.add(name)
        position = found.end()
    parts.append(re.escape(english[position:]))
    if not {m.group(2) for m in _PLACEHOLDER.finditer(german)} <= names:
        raise ValueError(f"German template uses a placeholder the English lacks: {english!r}")
    return Template(english, german, re.compile("".join(parts)), frozenset(recursive))


@dataclass(frozen=True)
class Catalogue:
    exact: dict[str, str]
    fragments: dict[str, str]
    #: Keyed by the first `_PREFIX` characters of the English; "" for a leading placeholder.
    #: Every bucket also holds the "" templates, so one lookup finds every candidate.
    buckets: dict[str, tuple[Template, ...]]


def _bucket_key(english: str) -> str:
    literal = english.split("{", 1)[0]
    return literal[:_PREFIX] if len(literal) >= _PREFIX else ""


def _specificity(template: Template) -> tuple[int, str]:
    """The more literal text a template has, the more specific it is: tried first."""
    return -len(_PLACEHOLDER.sub("", template.english)), template.english


def build_catalogue(entries: dict[str, str], fragments: dict[str, str]) -> Catalogue:
    exact: dict[str, str] = {}
    grouped: dict[str, list[Template]] = {"": []}
    for english, german_text in entries.items():
        if _PLACEHOLDER.search(english) is None:
            exact[english] = german_text
            continue
        template = compile_template(english, german_text)
        grouped.setdefault(_bucket_key(english), []).append(template)
    loose = grouped[""]
    buckets = {
        key: tuple(sorted({*group, *loose}, key=_specificity)) for key, group in grouped.items()
    }
    return Catalogue(exact, dict(fragments), buckets)


def merged(modules: tuple[ModuleType, ...]) -> tuple[dict[str, str], dict[str, str]]:
    """Every module's entries and fragments; an entry catalogued twice is a mistake."""
    entries: dict[str, str] = {}
    fragments: dict[str, str] = {}
    for module in modules:
        clash = entries.keys() & module.ENTRIES.keys()
        if clash:
            raise ValueError(f"{module.__name__} repeats catalogue entries: {sorted(clash)[:3]}")
        entries.update(module.ENTRIES)
        fragments.update(getattr(module, "FRAGMENTS", {}))
    return entries, fragments


@lru_cache(maxsize=1)
def german() -> Catalogue:
    return build_catalogue(*merged(MODULES))


def _match(text: str, catalogue: Catalogue, depth: int) -> str | None:
    found = catalogue.exact.get(text)
    if found is not None:
        return found
    candidates = catalogue.buckets.get(text[:_PREFIX]) or catalogue.buckets.get("", ())
    for template in candidates:
        match = template.pattern.fullmatch(text)
        if match is not None:
            return template.fill(match, depth)
    return None


def _by_sentences(text: str, depth: int) -> str | None:
    """Sentence by sentence; the longest run the catalogue knows word for word wins."""
    sentences = _SENTENCE_END.split(text)
    if len(sentences) < 2:
        return None
    exact = german().exact
    parts: list[str] = []
    start = 0
    while start < len(sentences):
        for end in range(len(sentences), start + 1, -1):
            known = exact.get(" ".join(sentences[start:end]))
            if known is not None:
                parts.append(known)
                start = end
                break
        else:
            parts.append(_translate(sentences[start], depth + 1))
            start += 1
    joined = " ".join(parts)
    return joined if joined != text else None


def _by_label(text: str, depth: int) -> str | None:
    """``"<a known title>: <detail>"``, as a preflight refusal writes each failed check."""
    head, colon, tail = text.partition(": ")
    if not colon:
        return None
    translated = _translate(head, depth + 1)
    if translated == head:
        return None
    return f"{translated}: {_translate(tail, depth + 1)}"


def _translate(text: str, depth: int, *, fragment: bool = False) -> str:
    catalogue = german()
    if fragment and text in catalogue.fragments:
        return catalogue.fragments[text]
    if depth > _MAX_DEPTH or not text.strip():
        return text
    matched = _match(text, catalogue, depth)
    if matched is not None:
        return matched
    return _by_sentences(text, depth) or _by_label(text, depth) or text


def translate_text(text: str, lang: str) -> str:
    """`text` in `lang` when the catalogue knows it; otherwise `text` unchanged."""
    if not lang.lower().startswith("de"):
        return text
    return _translate(text, 0)


__all__ = [
    "MODULES",
    "Catalogue",
    "Template",
    "build_catalogue",
    "compile_template",
    "german",
    "merged",
    "translate_text",
]
