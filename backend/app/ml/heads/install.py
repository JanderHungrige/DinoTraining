"""Installing a pinned first-party head — the trusted half of doc 15.

Trust here rests on one thing only: the SHA-256 in :mod:`app.ml.heads.catalog` was
computed from the real file, and :mod:`app.ml.heads.convert` verifies it *before*
torch reads a byte. The URL comes from the catalogue, never from a caller.

The downloaded ``.pth`` exists only inside :func:`_fetch_and_convert` and is gone
before it returns, so no pickle survives anywhere in the app's data directory.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from torch import Tensor

from app.core.config import Settings, get_settings
from app.ml.backbone import read_capabilities
from app.ml.heads.catalog import CatalogEntry, get_catalog_entry
from app.ml.heads.convert import download_entry, load_verified_state_dict, remap_state_dict
from app.ml.heads.instances import HeadInstance
from app.ml.heads.register import register_head, require_compatible, require_spec
from app.ml.heads.store import HeadInstanceStore

logger = logging.getLogger(__name__)

#: Recorded as the source repo for every catalogue head. Matches the ``owner/name``
#: shape a community import records, so a picker showing both reads consistently.
UPSTREAM_PROJECT = "facebookresearch/dinov2"


def install_catalog_entry(entry_id: str, settings: Settings | None = None) -> HeadInstance:
    """Download, verify, convert and register one pinned default head."""
    settings = settings or get_settings()

    entry = get_catalog_entry(entry_id)
    if entry is None:
        raise LookupError(f"Unknown catalogue entry: {entry_id}")

    spec = require_spec(entry.head_type_id)
    # Checked before the download, not after: fetching several MB for a backbone the
    # user has not installed spends their bandwidth to reach the same refusal.
    capabilities = read_capabilities(entry.backbone_id)
    require_compatible(spec, capabilities)

    if _already_installed(entry, settings):
        raise FileExistsError(f"{entry.id} is already installed")

    weights = _fetch_and_convert(entry)

    return register_head(
        spec=spec,
        capabilities=capabilities,
        weights=weights,
        num_classes=None,  # fixed upstream label set; the builder supplies it
        kind="pretrained-default",
        # spec.title already names the dataset ("… (NYUd)"), so appending trained_on
        # would double-parenthesise it.
        name=spec.title,
        # The upstream *project*, not the file URL. HeadInstance.summary renders this
        # in every picker, and a URL there puts a .pth filename in front of the user —
        # exactly what doc 12's cross-tab contract exists to prevent. The exact URL is
        # kept in config below, where provenance is auditable without being displayed.
        source_repo=UPSTREAM_PROJECT,
        source_digest=entry.sha256,
        config={
            "catalog_entry_id": entry.id,
            "source_url": entry.url,
            "trained_on": entry.trained_on,
            "licence": entry.licence,
            **({"depth_range": list(entry.depth_range)} if entry.depth_range else {}),
        },
        settings=settings,
    )


def _already_installed(entry: CatalogEntry, settings: Settings) -> bool:
    """Has this default already been installed for this backbone?

    Matched on (head type, backbone, kind) rather than on the weights path, so the
    check survives the store choosing a different filename.
    """
    existing = HeadInstanceStore(settings).list_all(backbone_id=entry.backbone_id)
    return any(
        item.head_type_id == entry.head_type_id and item.kind == "pretrained-default"
        for item in existing
    )


def _fetch_and_convert(entry: CatalogEntry) -> dict[str, Tensor]:
    """Download to a temp dir, convert, and leave no pickle behind.

    The ``.pth`` lives only inside this function. Staging it in the model cache would
    leave a pickle on disk that some later code path could find and load — which is
    the property doc 12 relies on when it says the head loader has no pickle branch.
    """
    with tempfile.TemporaryDirectory(prefix="dino-head-") as staging:
        destination = Path(staging) / f"{entry.id}.pth"
        download_entry(entry, destination)
        raw = load_verified_state_dict(destination, entry.sha256)
        converted = remap_state_dict(entry.head_type_id, raw)
        # Materialised before the temp dir disappears: torch tensors read from a file
        # can be views onto storage that is about to be unlinked.
        return {key: value.clone() for key, value in converted.items()}
