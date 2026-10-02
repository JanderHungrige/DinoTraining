"""Pascal VOC as COCO documents (doc 136).

One XML per picture: `<annotation><filename>`, `<size><width><height>`, and an `<object>`
per box with `<name>` and `<bndbox><xmin><ymin><xmax><ymax>`. The picture is beside the
XML, or in the VOC layout's `JPEGImages` next to `Annotations`.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Any

from app.cloud.pictures import picture_exists
from app.datasets.coco_import import split_of
from app.datasets.intake.documents import Document
from app.datasets.intake.walk import Listing

logger = logging.getLogger(__name__)


def _parse(path: Path) -> ElementTree.Element | None:
    try:
        root = ElementTree.parse(path).getroot()  # noqa: S314 - local files the user chose
    except (ElementTree.ParseError, OSError):
        return None
    return root if root.tag == "annotation" and root.find("object") is not None else None


def is_voc(listing: Listing) -> bool:
    return any(_parse(path) is not None for path in listing.xml_files[:20])


def _picture_for(xml: Path, element: ElementTree.Element) -> Path | None:
    name = (element.findtext("filename") or "").strip()
    if not name:
        return None
    for folder in (
        xml.parent,
        xml.parent.with_name("JPEGImages"),
        xml.parent.parent / "JPEGImages",
    ):
        if picture_exists(folder / name):  # a bucket's picture is listed, not local (doc 148)
            return folder / name
    return None


def voc_documents(listing: Listing) -> list[Document]:
    by_split: dict[str | None, dict[str, Any]] = {}
    for xml in listing.xml_files:
        element = _parse(xml)
        picture = _picture_for(xml, element) if element is not None else None
        if element is None or picture is None:
            continue
        relative = picture.relative_to(listing.root)
        split = next(
            (split_of(p) for p in xml.relative_to(listing.root).parts if split_of(p)), None
        )
        doc = by_split.setdefault(split, {"images": [], "annotations": [], "categories": []})
        size = element.find("size")
        width = int(float(size.findtext("width") or 0)) if size is not None else 0
        height = int(float(size.findtext("height") or 0)) if size is not None else 0
        image_id = len(doc["images"]) + 1
        doc["images"].append(
            {"id": image_id, "file_name": str(relative), "width": width, "height": height}
        )
        for obj in element.findall("object"):
            box = obj.find("bndbox")
            name = (obj.findtext("name") or "").strip()
            if box is None or not name:
                continue
            x1, y1, x2, y2 = (
                float(box.findtext(key) or 0) for key in ("xmin", "ymin", "xmax", "ymax")
            )
            doc["annotations"].append(
                {
                    "id": len(doc["annotations"]) + 1,
                    "image_id": image_id,
                    "category_id": _category(doc, name),
                    "bbox": [x1, y1, x2 - x1, y2 - y1],
                }
            )
    return [
        Document(doc, listing.root, listing.root / "Annotations", split)
        for split, doc in by_split.items()
    ]


def _category(doc: dict[str, Any], name: str) -> int:
    for category in doc["categories"]:
        if category["name"] == name:
            return int(category["id"])
    doc["categories"].append({"id": len(doc["categories"]) + 1, "name": name})
    return len(doc["categories"])
