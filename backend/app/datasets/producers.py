"""Encoding the producer snapshot for storage.

One column, JSON text — the same shape `head_instances.metrics` and `.config` already
use, so there is one convention for structured values in this schema rather than two.

Both directions live here because they must agree, and a mismatch would surface as a
validation error while *reading back* data this application itself wrote.
"""

from __future__ import annotations

import json
import logging

from app.datasets.models import Producer

logger = logging.getLogger(__name__)


def encode_producer(producer: Producer | None) -> str | None:
    """Model to column value. ``None`` stays ``None`` — a hand-drawn box has no producer."""
    return None if producer is None else producer.model_dump_json(exclude_none=True)


def decode_producer(raw: object) -> Producer | None:
    """Column value to model.

    A row written before this column existed is ``NULL``, and a row written by a future
    version may carry fields this one does not know; neither is worth failing a read for,
    so both degrade to ``None`` with a log line rather than raising.
    """
    if raw is None or raw == "":
        return None
    try:
        return Producer.model_validate(json.loads(str(raw)))
    except (ValueError, TypeError):
        logger.warning("Ignoring unreadable producer snapshot: %r", raw)
        return None
