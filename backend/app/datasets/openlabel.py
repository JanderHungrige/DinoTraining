"""Reading ASAM OpenLABEL multi-sensor annotations as single-camera detection boxes.

OSDaR23 and the rail datasets that follow it publish **OpenLABEL** JSON, not COCO: one file
per subsequence describing every object across every sensor — several RGB cameras, several
infrared cameras, lidar and radar — with each annotation tagged by the `coordinate_system`
it belongs to. Doc 31's importer reads COCO and nothing else, so this converts rather than
adding a second import path: OpenLABEL -> COCO -> the importer that already exists.

Three decisions here are the whole module, and each one silently produces a plausible-
looking dataset if it goes the other way.

**One camera at a time.** Every annotation carries a `coordinate_system`, and the same
physical object is annotated separately in each sensor that can see it. Ignoring the field
would multiply every object by the number of sensors and pair boxes from one camera with
images from another — a dataset that trains, and learns nothing.

**Boxes are centre-based here and corner-based in COCO.** OpenLABEL's `bbox.val` is
`[cx, cy, w, h]`; COCO's is `[x, y, w, h]` from the top-left. Missing that shifts every box
by half its own size, which is small enough to look like ordinary annotation noise.

**A closed `poly2d` is a box; an open one is not.** OSDaR23 annotates signals as closed
four-point quads — those have a meaningful extent. It annotates *track* as an open polyline
running to the horizon, and that extent is a huge diagonal rectangle containing mostly
ballast and vegetation. Boxing it would teach a detector that "track" means "most of the
image", and would poison every other class's background along with it.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: What every OSDaR23 archive calls its annotation file.
LABELS_SUFFIX = "_labels.json"

#: Smaller than this in either dimension and the box is dropped. A 2 px annotation carries
#: no appearance for a backbone to learn from, and it still costs a detector a false
#: negative it can never avoid.
MIN_BOX_PIXELS = 4.0


@dataclass(frozen=True, slots=True)
class ConversionSummary:
    """What the conversion produced, and what it refused.

    The skip counters are returned rather than logged for doc 31's reason: a lossy
    conversion that reports success is indistinguishable from a clean one at the call site.
    """

    images: int = 0
    boxes: int = 0
    class_names: tuple[str, ...] = ()
    skipped_open_polylines: int = 0
    skipped_tiny: int = 0
    skipped_other_sensors: int = 0
    excluded_classes: tuple[str, ...] = field(default=())


def load_openlabel(path: Path) -> dict[str, Any]:
    """Parse one OpenLABEL file, checking it is one."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is not valid JSON: {exc}") from exc

    root = payload.get("openlabel")
    if not isinstance(root, dict):
        raise ValueError(f"{path.name} has no 'openlabel' object — is it OpenLABEL?")
    for key in ("objects", "frames"):
        if not isinstance(root.get(key), dict):
            raise ValueError(f"{path.name} has no '{key}' — nothing to convert")
    return root


def camera_names(root: dict[str, Any]) -> tuple[str, ...]:
    """Every stream declared as a camera, so a caller can offer a real choice."""
    streams = root.get("streams")
    if not isinstance(streams, dict):
        return ()
    return tuple(
        sorted(
            name
            for name, spec in streams.items()
            if isinstance(spec, dict) and spec.get("type") == "camera"
        )
    )


def frame_image(frame: dict[str, Any], camera: str) -> str | None:
    """The image this frame's `camera` stream points at, as a relative path."""
    streams = frame.get("frame_properties", {}).get("streams", {})
    uri = streams.get(camera, {}).get("uri")
    if not isinstance(uri, str) or not uri:
        return None
    # OpenLABEL writes these rooted at the archive ("/rgb_center/000_….png"); the importer
    # resolves file names relative to the annotation file, so the leading slash must go or
    # every path would escape the dataset folder.
    return uri.lstrip("/")


def box_from_bbox(entry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """`[cx, cy, w, h]` -> `[x, y, w, h]` from the top-left."""
    val = entry.get("val")
    if not isinstance(val, list) or len(val) != 4:
        return None
    try:
        cx, cy, w, h = (float(v) for v in val)
    except (TypeError, ValueError):
        return None
    return (cx - w / 2.0, cy - h / 2.0, w, h)


def box_from_poly2d(entry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """The extent of a **closed** polygon. Open polylines return None on purpose."""
    if not entry.get("closed"):
        return None
    val = entry.get("val")
    if not isinstance(val, list) or len(val) < 6 or len(val) % 2:
        return None
    try:
        coordinates = [float(v) for v in val]
    except (TypeError, ValueError):
        return None
    xs, ys = coordinates[0::2], coordinates[1::2]
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


__all__ = [
    "LABELS_SUFFIX",
    "MIN_BOX_PIXELS",
    "ConversionSummary",
    "box_from_bbox",
    "box_from_poly2d",
    "camera_names",
    "frame_image",
    "load_openlabel",
]
