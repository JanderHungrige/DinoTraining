"""Detect and import a bucket's dataset (doc 148): doc 136's intake on a bucket's listing."""

from __future__ import annotations

import threading
from collections.abc import Callable

from app.cloud.connections import get_connection
from app.cloud.links import Link, create_link, get_link, set_dataset
from app.cloud.remote_listing import remote_listing
from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.exchange.cloud_export import current_e_tags
from app.datasets.exchange.dump import dump_dataset
from app.datasets.exchange.layout import EXPORT_DIR, find_export
from app.datasets.exchange.targets import Target, record_bucket, set_target
from app.datasets.intake.detect import Detection, scan
from app.datasets.intake.importer import ImportResult, run_import
from app.datasets.intake.walk import Listing

Progress = Callable[[int, int, str], None]

#: The listing made by a detection, kept for the import that follows it.
_listings: dict[str, Listing] = {}
_lock = threading.Lock()


def detect_link(
    connection_id: str, bucket: str, prefix: str, settings: Settings | None = None
) -> tuple[Link, Detection]:
    link = create_link(connection_id, bucket, prefix, settings)
    listing = remote_listing(link)
    with _lock:
        _listings[link.id] = listing
    detection, _documents, _listing = scan(link.cache_root, listing)
    return link, detection.model_copy(
        update={"path": link.uri, "name": detection.name if prefix else bucket}
    )


def import_link(
    link_id: str,
    name: str,
    description: str | None,
    progress: Progress,
    settings: Settings | None = None,
) -> ImportResult:
    link = get_link(link_id, settings)
    with _lock:
        listing = _listings.pop(link_id, None)
    if listing is None:  # the backend restarted since the detection: list again
        listing = remote_listing(link, progress)
    connection = get_connection(link.connection_id, settings)
    text = (description or "").strip() or f"Linked from {link.uri} ({connection.name})."
    result = run_import(link.cache_root, name, text, False, progress, settings, listing=listing)
    set_dataset(link.id, result.dataset_id, settings)
    with transaction(settings) as db:
        db.execute("UPDATE datasets SET source = ? WHERE id = ?", (link.uri, result.dataset_id))
    # After every write to the dataset: the baseline's fingerprint must be its final state.
    _save_back_by_default(link, result.dataset_id, settings)
    return result


def _save_back_by_default(link: Link, dataset_id: str, settings: Settings | None) -> None:
    """Doc 150: a linked dataset saves back into its bucket; restored from an export there,
    it starts from that export's ETags, so its first save-back is an update."""
    set_target(dataset_id, Target(kind="data"), settings)
    if find_export(link.cache_root) is not None:
        folder = f"{link.uri}/{EXPORT_DIR}"
        dump = dump_dataset(dataset_id, settings)
        record_bucket(dataset_id, folder, current_e_tags(link, settings), dump, settings)
