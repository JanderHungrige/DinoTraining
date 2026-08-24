"""Fetch, verify and convert first-party head weights to safetensors.

**This module contains the only ``torch.load`` in the application.** Reading a pickle
is arbitrary code execution, so the carve-out is narrow and stated precisely:

1. the URL comes from the pinned catalogue, never from a caller;
2. the SHA-256 is verified **before** the bytes are handed to torch;
3. ``weights_only=True`` is used even then, with a fixed allowlist of numpy scalar
   constructors — never ``weights_only=False``;
4. the ``.pth`` is deleted after conversion, so no pickle survives on disk.

Move the digest check after the load and property 2 is gone, which is the whole
argument. A test asserts the ordering directly rather than trusting review.

Community imports do not come through here at all — see :mod:`app.ml.heads.importer`,
where pickles are refused outright rather than verified.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from torch import Tensor

from app.ml.heads.catalog import PINNED_HOST, CatalogEntry

logger = logging.getLogger(__name__)

_CHUNK = 1 << 20  # 1 MiB
_DOWNLOAD_TIMEOUT_SECONDS = 120


class DigestMismatchError(ValueError):
    """The downloaded bytes are not the bytes we pinned. Never proceed past this."""


class UnsupportedCheckpointError(ValueError):
    """The checkpoint does not have the structure this head type expects."""


class UpstreamUnavailableError(RuntimeError):
    """The pinned host could not be reached."""


def verify_digest(path: Path, expected_sha256: str) -> str:
    """Hash ``path`` and compare against ``expected_sha256``. Returns the digest.

    Streamed rather than read whole: these files reach 8 MB now and a future entry
    could be far larger, and there is no reason to hold one in memory to hash it.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    actual = digest.hexdigest()

    if actual != expected_sha256.lower():
        # Both digests in the message: "digest mismatch" alone gives whoever hits this
        # no way to tell a corrupted download from a changed upstream file.
        raise DigestMismatchError(
            f"Digest mismatch for {path.name}: expected {expected_sha256.lower()}, "
            f"got {actual}. The file was not read."
        )
    return actual


def download_entry(entry: CatalogEntry, destination: Path) -> Path:
    """Download one catalogue entry to ``destination``, then verify its digest.

    The URL is asserted against the pinned host even though it comes from the
    catalogue — a future edit that parameterises it must not silently become a
    caller-supplied fetch.
    """
    if not entry.url.startswith(f"https://{PINNED_HOST}/"):
        raise ValueError(f"Refusing to fetch {entry.id} from outside {PINNED_HOST}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading head %s (%d bytes)", entry.id, entry.size_bytes)

    try:
        with urllib.request.urlopen(  # noqa: S310 - scheme and host asserted above
            entry.url, timeout=_DOWNLOAD_TIMEOUT_SECONDS
        ) as response, destination.open("wb") as handle:
            shutil.copyfileobj(response, handle, _CHUNK)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        destination.unlink(missing_ok=True)
        # Report the class, not the text: an upstream error can embed a signed URL.
        logger.exception("Download failed for head %s", entry.id)
        raise UpstreamUnavailableError(
            f"Could not download {entry.id} from {PINNED_HOST}: {type(exc).__name__}"
        ) from exc

    try:
        verify_digest(destination, entry.sha256)
    except DigestMismatchError:
        # A file that failed verification must not be left where a later run could
        # find it and assume it is good.
        destination.unlink(missing_ok=True)
        raise

    return destination


def _safe_globals() -> list[Any]:
    """The fixed allowlist needed to read DINOv2's depth checkpoints.

    Those files embed a numpy scalar, so ``weights_only=True`` rejects them outright
    without this. The alternative — ``weights_only=False`` — would re-enable arbitrary
    code execution for the sake of two floats, which is not a trade worth making.

    The pickle names the constructor ``numpy.core.multiarray.scalar``, but numpy 2.x
    moved it to ``numpy._core``. torch keys its allowlist off the object's own module
    path, so the legacy name has to be supplied explicitly as an alias.
    """
    import numpy as np
    import numpy._core.multiarray as multiarray

    allowed: list[Any] = [
        (multiarray.scalar, "numpy.core.multiarray.scalar"),
        (np.dtype, "numpy.dtype"),
    ]
    # Dtype classes vary by numpy build; take whichever exist rather than assuming.
    for name in ("Float64DType", "Float32DType", "Int64DType"):
        dtype_class = getattr(np.dtypes, name, None)
        if dtype_class is not None:
            allowed.append(dtype_class)
    return allowed


def load_verified_state_dict(path: Path, expected_sha256: str) -> dict[str, Tensor]:
    """Verify then read a pinned checkpoint. **Verification happens first.**"""
    verify_digest(path, expected_sha256)

    import torch

    torch.serialization.add_safe_globals(_safe_globals())
    loaded = torch.load(path, map_location="cpu", weights_only=True)

    if isinstance(loaded, Mapping) and "state_dict" in loaded:
        loaded = loaded["state_dict"]

    if not isinstance(loaded, Mapping):
        raise UnsupportedCheckpointError(
            f"{path.name} does not contain a state dict (got {type(loaded).__name__})"
        )

    return {str(key): value for key, value in loaded.items()}


# --- key remapping ---------------------------------------------------------------
#
# Keyed by head-type id, never an if/elif on task — the same registry discipline the
# rest of the wave uses. Each entry maps upstream key -> our module's parameter name.

_CLASSIFIER_KEYS = {
    "weight": "linear.weight",
    "bias": "linear.bias",
}

_SEGMENTER_KEYS = {
    "decode_head.bn.weight": "bn.weight",
    "decode_head.bn.bias": "bn.bias",
    "decode_head.bn.running_mean": "bn.running_mean",
    "decode_head.bn.running_var": "bn.running_var",
    "decode_head.bn.num_batches_tracked": "bn.num_batches_tracked",
    "decode_head.conv_seg.weight": "conv_seg.weight",
    "decode_head.conv_seg.bias": "conv_seg.bias",
}

_DEPTH_KEYS = {
    "decode_head.conv_depth.weight": "conv_depth.weight",
    "decode_head.conv_depth.bias": "conv_depth.bias",
}

KEY_MAPS: dict[str, dict[str, str]] = {
    "dinov2-linear-classifier-in1k": _CLASSIFIER_KEYS,
    "dinov2-linear-segmenter-ade20k": _SEGMENTER_KEYS,
    "dinov2-linear-depth-nyu": _DEPTH_KEYS,
}


def remap_state_dict(head_type_id: str, raw: Mapping[str, Tensor]) -> dict[str, Tensor]:
    """Rename upstream keys onto our module's parameter names.

    Both missing and unexpected keys are errors. Dropping an unexpected key would let
    a checkpoint load into a head that is only partly initialised — which produces
    plausible output and no failure anywhere.
    """
    mapping = KEY_MAPS.get(head_type_id)
    if mapping is None:
        raise LookupError(f"No key map for head type: {head_type_id}")

    missing = sorted(set(mapping) - set(raw))
    unexpected = sorted(set(raw) - set(mapping))
    if missing or unexpected:
        raise UnsupportedCheckpointError(
            f"{head_type_id}: checkpoint does not match the expected layout. "
            f"Missing {missing or 'nothing'}; unexpected {unexpected or 'nothing'}."
        )

    return {mapping[key]: raw[key] for key in mapping}
