"""A class name as training sees it (docs 11, 81).

One function, used by the trainer and the data audit alike: if the audit counted `Signal`
and `signal.` as two classes while training merged them, the report would describe a
dataset that training never sees.
"""

from __future__ import annotations

import re

#: What an annotation with no class name is trained as.
UNNAMED_CLASS = "object"


def normalise_class_name(prompt: str | None) -> str:
    """Lower case, surrounding space and a trailing full stop dropped."""
    name = (prompt or "").strip().lower().rstrip(".")
    return name or UNNAMED_CLASS


def spelling_key(name: str) -> str:
    """What two spellings of one class share: separators unified, a plural 's' dropped.

    `traffic-light`, `traffic_light` and `traffic lights` share a key. Used to *propose*
    merges (docs 81, 82), never to merge silently: `glass` and `glasses` share one too.
    """
    key = re.sub(r"[\s_\-]+", " ", normalise_class_name(name)).strip()
    return key[:-1] if key.endswith("s") and len(key) > 3 else key


__all__ = ["UNNAMED_CLASS", "normalise_class_name", "spelling_key"]
