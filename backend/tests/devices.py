"""Which accelerators a test can really use on this machine.

`is_available()` is not enough: GitHub's macOS runners report MPS but cannot allocate on
it ("MPS backend out of memory ... max allowed: 7.93 GiB" for 256 bytes).
"""

from __future__ import annotations

import torch


def mps_usable() -> bool:
    if not torch.backends.mps.is_available():
        return False
    try:
        torch.zeros(1, device="mps")
    except RuntimeError:
        return False
    return True
