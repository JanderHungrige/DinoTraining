"""The facts a dataset audit is built from, read in one pass (doc 81).

SQL does the reading and nothing else: one query for the images, one for every annotation
with its size and verdict. The rules in ``findings.py`` are pure functions over what this
returns, so they can be tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

from app.core.config import Settings
from app.datasets.class_names import normalise_class_name
from app.datasets.db import transaction


@dataclass(frozen=True, slots=True)
class ImageFacts:
    id: int
    path: str
    width: int
    height: int
    sequence: str | None


@dataclass(frozen=True, slots=True)
class AnnotationFacts:
    image_id: int
    #: "box" or "mask".
    kind: str
    #: "positive", "negative" or "unclear".
    label: str
    #: The class as training will see it (`normalise_class_name`).
    cls: str
    #: The class as it was written, for spotting near-identical spellings.
    raw: str
    width: float
    height: float
    x: float
    y: float


@dataclass
class DatasetFacts:
    dataset_id: str
    images: list[ImageFacts] = field(default_factory=list)
    annotations: list[AnnotationFacts] = field(default_factory=list)
    #: Images a safe fix took out (doc 83). Not in `images`: everything downstream of a fix
    #: should see the dataset as training will.
    excluded: int = 0

    def positives(self) -> list[AnnotationFacts]:
        return [a for a in self.annotations if a.label == "positive"]

    def image(self, image_id: int) -> ImageFacts | None:
        return self._by_id.get(image_id)

    def signature(self, image_id: int) -> tuple[tuple[str, str, int, int, int, int], ...]:
        """What an image is annotated with, coarse enough that a re-saved copy matches.

        Positions are on a 50-step grid of the image, so a copy resized to another
        resolution has the same signature and a different object does not.
        """
        image = self.image(image_id)
        if image is None:
            return ()
        w, h = max(1, image.width), max(1, image.height)
        return tuple(
            sorted(
                (
                    a.cls,
                    a.label,
                    round(a.x / w * 50),
                    round(a.y / h * 50),
                    round(a.width / w * 50),
                    round(a.height / h * 50),
                )
                for a in self._annotations_by_image.get(image_id, [])
            )
        )

    @cached_property
    def _annotations_by_image(self) -> dict[int, list[AnnotationFacts]]:
        grouped: dict[int, list[AnnotationFacts]] = {}
        for annotation in self.annotations:
            grouped.setdefault(annotation.image_id, []).append(annotation)
        return grouped

    @cached_property
    def _by_id(self) -> dict[int, ImageFacts]:
        # Built once: rules look an image up per annotation, and rebuilding the index each
        # time would make a 50,000-box audit quadratic.
        return {image.id: image for image in self.images}


_INCLUDED = "COALESCE(i.excluded, 0) = 0"

_ANNOTATIONS = f"""
SELECT b.image_id, 'box' AS kind, b.label, b.prompt, b.x, b.y, b.w, b.h
  FROM boxes b JOIN images i ON i.id = b.image_id WHERE i.dataset_id = ? AND {_INCLUDED}
UNION ALL
SELECT m.image_id, 'mask', m.label, m.prompt, m.x, m.y, m.w, m.h
  FROM masks m JOIN images i ON i.id = m.image_id WHERE i.dataset_id = ? AND {_INCLUDED}
"""


def collect(
    dataset_id: str,
    settings: Settings | None = None,
    class_map: dict[str, str | None] | None = None,
) -> DatasetFacts:
    """The dataset as training will see it: excluded images left out, the class map applied
    (a class mapped to None is left out too)."""
    mapping = class_map or {}
    with transaction(settings) as connection:
        images = connection.execute(
            "SELECT id, path, width, height, sequence FROM images i"
            f" WHERE dataset_id = ? AND {_INCLUDED} ORDER BY id",
            (dataset_id,),
        ).fetchall()
        excluded = connection.execute(
            f"SELECT COUNT(*) FROM images i WHERE dataset_id = ? AND NOT {_INCLUDED}",
            (dataset_id,),
        ).fetchone()[0]
        annotations = connection.execute(_ANNOTATIONS, (dataset_id, dataset_id)).fetchall()
    return DatasetFacts(
        dataset_id=dataset_id,
        excluded=int(excluded),
        images=[
            ImageFacts(
                id=int(row["id"]),
                path=str(row["path"]),
                width=int(row["width"]),
                height=int(row["height"]),
                sequence=row["sequence"],
            )
            for row in images
        ],
        annotations=[
            AnnotationFacts(
                image_id=int(row["image_id"]),
                kind=str(row["kind"]),
                label=str(row["label"]),
                cls=cls,
                raw=str(row["prompt"] or ""),
                x=float(row["x"]),
                y=float(row["y"]),
                width=float(row["w"]),
                height=float(row["h"]),
            )
            for row in annotations
            if (cls := _mapped(row["prompt"], mapping)) is not None
        ],
    )


def _mapped(prompt: str | None, mapping: dict[str, str | None]) -> str | None:
    name = normalise_class_name(prompt)
    return mapping.get(name, name) if name in mapping else name


__all__ = ["AnnotationFacts", "DatasetFacts", "ImageFacts", "collect"]
