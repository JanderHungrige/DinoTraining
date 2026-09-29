"""A class name as training sees it (docs 11, 81).

One function, used by the trainer and the data audit alike: if the audit counted `Signal`
and `signal.` as two classes while training merged them, the report would describe a
dataset that training never sees.
"""

from __future__ import annotations

#: What an annotation with no class name is trained as.
UNNAMED_CLASS = "object"


def normalise_class_name(prompt: str | None) -> str:
    """Lower case, surrounding space and a trailing full stop dropped."""
    name = (prompt or "").strip().lower().rstrip(".")
    return name or UNNAMED_CLASS


__all__ = ["UNNAMED_CLASS", "normalise_class_name"]
