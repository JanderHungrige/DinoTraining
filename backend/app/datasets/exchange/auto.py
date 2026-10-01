"""Export every changed dataset to its target: on closing, every n minutes, on demand (doc 144).

One run at a time. A deadline leaves datasets that would start after it for the next run,
reported as unfinished; one already writing is never cut off (doc 142's atomic writes).
The last report is kept in the data folder, so the next start can name what did not go.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from app.core.config import Settings
from app.datasets.db import data_root, transaction
from app.datasets.exchange.dump import dump_dataset, fingerprint
from app.datasets.exchange.targets import Exported, export_to_target

logger = logging.getLogger(__name__)

REPORT_FILE = "auto_export.json"


class Named(BaseModel):
    dataset_id: str
    name: str


class Failed(Named):
    error: str


class AutoReport(BaseModel):
    started_at: str
    finished_at: str | None = None
    #: "close", "interval" or "manual": who asked.
    reason: str
    exported: list[Named] = []
    unchanged: int = 0
    failed: list[Failed] = []
    unfinished: list[Named] = []
    no_target: list[Named] = []


_lock = threading.Lock()
_running = threading.Event()


def report_path(settings: Settings | None = None) -> Path:
    return data_root(settings) / REPORT_FILE


def last_report(settings: Settings | None = None) -> AutoReport | None:
    path = report_path(settings)
    try:
        return (
            AutoReport.model_validate_json(path.read_text(encoding="utf-8"))
            if path.is_file()
            else None
        )
    except ValueError:
        logger.warning("Ignoring an unreadable %s", path)
        return None


def is_running() -> bool:
    return _running.is_set()


def _datasets(settings: Settings | None) -> list[tuple[str, str, str | None, str | None]]:
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT d.id, d.name, d.export_target, d.exported FROM datasets d"
            " WHERE EXISTS (SELECT 1 FROM images i"
            "  WHERE i.dataset_id = d.id AND i.annotated_at != '')"
            " ORDER BY d.created_at"
        ).fetchall()
    return [(row["id"], row["name"], row["export_target"], row["exported"]) for row in rows]


def _changed(dataset_id: str, exported: str | None, settings: Settings | None) -> bool:
    if not exported:
        return True
    last = Exported.model_validate_json(exported)
    return last.fingerprint != fingerprint(dump_dataset(dataset_id, settings))


def _run(report: AutoReport, deadline: float | None, settings: Settings | None) -> None:
    for dataset_id, name, target, exported in _datasets(settings):
        named = Named(dataset_id=dataset_id, name=name)
        if target is None:
            report.no_target.append(named)
            continue
        if deadline is not None and time.monotonic() > deadline:
            report.unfinished.append(named)
            continue
        try:
            if not _changed(dataset_id, exported, settings):
                report.unchanged += 1
                continue
            export_to_target(dataset_id, settings)
            report.exported.append(named)
        except (ValueError, OSError) as error:
            logger.warning("Auto-export of %s failed: %s", name, error)
            report.failed.append(Failed(dataset_id=dataset_id, name=name, error=str(error)))


def run_exports(
    reason: str, deadline_seconds: float | None = None, settings: Settings | None = None
) -> AutoReport | None:
    """Run now and return the report; None if a run is already going."""
    if not _lock.acquire(blocking=False):
        return None
    return _execute(reason, deadline_seconds, settings)


def start_in_background(reason: str, settings: Settings | None = None) -> bool:
    """For the interval: start a run unless one is going; True if started."""
    if not _lock.acquire(blocking=False):  # the lock, not the flag: no window between them
        return False
    thread = threading.Thread(
        target=_execute, args=(reason, None, settings), name="auto-export", daemon=True
    )
    thread.start()
    return True


def _execute(reason: str, deadline_seconds: float | None, settings: Settings | None) -> AutoReport:
    """The run itself; the caller holds `_lock`, which this releases."""
    _running.set()
    report = AutoReport(started_at=datetime.now(UTC).isoformat(timespec="seconds"), reason=reason)
    try:
        deadline = time.monotonic() + deadline_seconds if deadline_seconds is not None else None
        _run(report, deadline, settings)
    except Exception:
        logger.exception("Auto-export (%s) stopped", reason)
        raise
    finally:
        report.finished_at = datetime.now(UTC).isoformat(timespec="seconds")
        _save(report, settings)
        _running.clear()
        _lock.release()
    logger.info(
        "Auto-export (%s): %d exported, %d unchanged, %d failed, %d unfinished, %d no target",
        reason,
        len(report.exported),
        report.unchanged,
        len(report.failed),
        len(report.unfinished),
        len(report.no_target),
    )
    return report


def _save(report: AutoReport, settings: Settings | None) -> None:
    try:
        path = report_path(settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.model_dump(), indent=1), encoding="utf-8")
    except OSError as error:
        logger.warning("Could not keep the auto-export report: %s", error)
