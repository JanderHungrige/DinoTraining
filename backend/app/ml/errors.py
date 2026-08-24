"""Errors shared across the ML layer.

``ModelNotInstalledError`` lives here rather than beside any one loader. Detectors
(Wave 1) and backbones (Wave 2) both raise it, and `api/v1/annotate.py` catches it to
return a 409. Two same-named classes in two modules would mean a caller catching one
silently misses the other — which surfaces as an opaque 500 instead of "download this
model first".
"""

from __future__ import annotations


class ModelNotInstalledError(LookupError):
    """The requested model has not been downloaded yet."""
