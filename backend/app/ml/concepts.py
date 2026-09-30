"""The separate things a prompt asks for.

"flame, reflection" asks for two things, as does "flame. reflection." Grounding DINO only
separates phrases at a full stop, and SAM 3 reads its whole text as one concept, so a
comma used to make two search terms one label (found by Jan, 2026-09-30). Every model
reads its prompt through this one split.
"""

from __future__ import annotations

import re


def prompt_terms(prompt: str) -> list[str]:
    """Lower-cased terms, split at full stops, commas, semicolons and line breaks."""
    parts = (part.strip() for part in re.split(r"[.,;\n]", prompt.lower()))
    return list(dict.fromkeys(part for part in parts if part))


__all__ = ["prompt_terms"]
