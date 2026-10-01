"""Example datasets the app can fetch in one click (doc 138).

Facts read from the FID move portal's CKAN API on 2026-10-01: the resource Jan linked,
its download URL and size (the server's `content-length`), and the package licence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

Variant = Literal["full", "rgb-center"]
VARIANTS: tuple[Variant, ...] = ("full", "rgb-center")


@dataclass(frozen=True)
class Example:
    example_id: str
    sequence: str
    url: str
    download_bytes: int
    page: str
    licence: str
    licence_url: str
    annotations_licence: str
    attribution: str


OSDAR23 = Example(
    example_id="osdar23",
    sequence="3_fire_site_3.4",
    url="https://download.data.fid-move.de/dzsf/osdar23/3_fire_site_3.4.zip",
    download_bytes=763_518_017,
    page="https://data.fid-move.de/dataset/osdar23/resource/068947d5-9036-410e-bbb7-9409c5fcb264",
    licence="CC BY-SA 3.0 DE",
    licence_url="https://creativecommons.org/licenses/by-sa/3.0/de/",
    # The archive's own license.md: sensor data (pictures, lidar, radar) CC BY-SA 3.0 DE,
    # annotation files CC0 1.0. The portal's package licence names only the first.
    annotations_licence="CC0 1.0",
    attribution=(
        "OSDaR23 (doi:10.57806/9mv146r0) by the German Centre for Rail Traffic Research at "
        "the Federal Railway Authority (DZSF), Digitale Schiene Deutschland / DB Netz AG and "
        "FusionSystems GmbH"
    ),
)

EXAMPLES: dict[str, Example] = {OSDAR23.example_id: OSDAR23}

_VARIANT_NAMES: dict[Variant, str] = {"full": "all sensors", "rgb-center": "RGB centre camera"}


def keeps(variant: Variant, member: str) -> bool:
    """A: every sensor (not the readme's preview pictures, which would import as data).
    B: the RGB centre camera and the labels (doc 49's choice)."""
    if variant == "full":
        return not member.startswith("readme_img/")
    return member.startswith("rgb_center/") or member.endswith("_labels.json")


def dataset_name(example: Example, variant: Variant) -> str:
    return f"OSDaR23 · {example.sequence} · {_VARIANT_NAMES[variant]}"


def description(example: Example, variant: Variant) -> str:
    return (
        f"OSDaR23 rail sequence {example.sequence}, {_VARIANT_NAMES[variant]}, from Hamburg. "
        f"{example.attribution}. Pictures and other sensor data: {example.licence} "
        f"({example.licence_url}), attribution required and adaptations shared alike; "
        f"annotations: {example.annotations_licence}. "
        f"Source: {example.page}"
    )


class ExampleView(BaseModel):
    example_id: str
    sequence: str
    download_bytes: int
    page: str
    licence: str
    licence_url: str
    annotations_licence: str
    attribution: str
    #: The variants already downloaded (importing them again does not download).
    downloaded: list[Variant]
    #: A download or import of this example still running (the page reattaches to it).
    running_job: str | None = None


def view(example: Example, downloaded: list[Variant], running_job: str | None) -> ExampleView:
    return ExampleView(
        example_id=example.example_id,
        sequence=example.sequence,
        download_bytes=example.download_bytes,
        page=example.page,
        licence=example.licence,
        licence_url=example.licence_url,
        annotations_licence=example.annotations_licence,
        attribution=example.attribution,
        downloaded=downloaded,
        running_job=running_job,
    )
