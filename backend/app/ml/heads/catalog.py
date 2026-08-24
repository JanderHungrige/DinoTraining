"""The curated, SHA-256-pinned catalogue of first-party head weights.

This table is the *only* source of downloadable head URLs, exactly as
:mod:`app.ml.registry` is for backbones: a request names a catalogue key, never a URL.

Every digest below was produced by downloading the real file and hashing it — they are
not copied from a manifest. That matters, because the digest is what makes reading a
pickle defensible: :mod:`app.ml.heads.convert` verifies it *before* torch touches the
bytes, so the trust is in bytes we can check rather than in the host serving them.

**No DINOv3 entries, deliberately.** Meta publishes DINOv3 heads only for ViT-7B/16 —
not the ViT-B/16 or ViT-L/16 this app ships — gated behind a per-user e-mailed URL list
and under the DINOv3 License rather than Apache-2.0. All three conditions fail, so
DINOv3 backbones are train-your-own only. A test asserts this stays a decision rather
than drifting into an accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

#: Meta's public CDN. Split out so the URL assertion in tests has something to compare
#: against, and so a host change is one edit rather than nine.
PINNED_HOST = "dl.fbaipublicfiles.com"

_BASE = f"https://{PINNED_HOST}/dinov2"

#: NYUd depth range in metres. Data rather than a module constant, because a KITTI
#: entry would need (0.001, 80.0) and the module must not have to know which it holds.
_NYU_RANGE = (0.001, 10.0)


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One downloadable first-party head. Immutable — a mutable digest is not a pin."""

    id: str
    head_type_id: str
    backbone_id: str
    url: str
    sha256: str
    size_bytes: int
    embed_dim: int
    num_classes: int | None
    trained_on: str
    licence: str = "Apache-2.0"
    depth_range: tuple[float, float] | None = None


def _entry(
    *,
    head_type_id: str,
    backbone_id: str,
    model: str,
    suffix: str,
    sha256: str,
    size_bytes: int,
    embed_dim: int,
    num_classes: int | None,
    trained_on: str,
    depth_range: tuple[float, float] | None = None,
) -> CatalogEntry:
    """Build one entry, assembling the URL from the upstream naming scheme."""
    filename = f"dinov2_{model}_{suffix}.pth"
    return CatalogEntry(
        id=f"{head_type_id}.{backbone_id}",
        head_type_id=head_type_id,
        backbone_id=backbone_id,
        url=f"{_BASE}/dinov2_{model}/{filename}",
        sha256=sha256,
        size_bytes=size_bytes,
        embed_dim=embed_dim,
        num_classes=num_classes,
        trained_on=trained_on,
        depth_range=depth_range,
    )


# The three upstream head families, across the three DINOv2 backbones this app ships.
# vitg14 also publishes heads but is not in the model registry, so it is out of scope.
_CLASSIFIER = "dinov2-linear-classifier-in1k"
_SEGMENTER = "dinov2-linear-segmenter-ade20k"
_DEPTH = "dinov2-linear-depth-nyu"

_ENTRIES: tuple[CatalogEntry, ...] = (
    # --- dinov2-small / ViT-S/14, embed_dim 384 ---------------------------------
    _entry(
        head_type_id=_CLASSIFIER,
        backbone_id="dinov2-small",
        model="vits14",
        suffix="linear_head",
        sha256="74d2e1e9e662cd2f614edb87866352fd956d0377f62ff2ba110e1e5e848b65b5",
        size_bytes=3_077_159,
        embed_dim=384,
        num_classes=1000,
        trained_on="ImageNet-1k, 1000 classes",
    ),
    _entry(
        head_type_id=_SEGMENTER,
        backbone_id="dinov2-small",
        model="vits14",
        suffix="ade20k_linear_head",
        sha256="67e10225e0bf1e2c6e8bc9e07020211ab58cbb4aa14efbaa32c52914931c4ade",
        size_bytes=719_673,
        embed_dim=384,
        num_classes=150,
        trained_on="ADE20k, 150 classes",
    ),
    _entry(
        head_type_id=_DEPTH,
        backbone_id="dinov2-small",
        model="vits14",
        suffix="nyu_linear_head",
        sha256="6062f6789bf73ac06458c1e6c6cb067790da09c78004a33245207f0ad5f7e93c",
        size_bytes=2_367_211,
        embed_dim=384,
        num_classes=None,
        trained_on="NYU Depth v2",
        depth_range=_NYU_RANGE,
    ),
    # --- dinov2-base / ViT-B/14, embed_dim 768 ----------------------------------
    _entry(
        head_type_id=_CLASSIFIER,
        backbone_id="dinov2-base",
        model="vitb14",
        suffix="linear_head",
        sha256="ea23eb0617ddd9e67ebfb007474d6de446ac58c50da08070bc2525eb5d57ca17",
        size_bytes=6_149_159,
        embed_dim=768,
        num_classes=1000,
        trained_on="ImageNet-1k, 1000 classes",
    ),
    _entry(
        head_type_id=_SEGMENTER,
        backbone_id="dinov2-base",
        model="vitb14",
        suffix="ade20k_linear_head",
        sha256="7c3545c3a6f79ccc130d075dfe66e84f8c32d72d2acd31fc218f8a15cd2c7b23",
        size_bytes=1_423_161,
        embed_dim=768,
        num_classes=150,
        trained_on="ADE20k, 150 classes",
    ),
    _entry(
        head_type_id=_DEPTH,
        backbone_id="dinov2-base",
        model="vitb14",
        suffix="nyu_linear_head",
        sha256="2ce8ccb154437ca5761d16d0609144828ed273afeb73bb776a388650e5e0b339",
        size_bytes=4_726_507,
        embed_dim=768,
        num_classes=None,
        trained_on="NYU Depth v2",
        depth_range=_NYU_RANGE,
    ),
    # --- dinov2-large / ViT-L/14, embed_dim 1024 --------------------------------
    _entry(
        head_type_id=_CLASSIFIER,
        backbone_id="dinov2-large",
        model="vitl14",
        suffix="linear_head",
        sha256="5b499079fe2c85b6b5d72cc01fe31f192e30302ef8e9c6d999a9513425abd5f1",
        size_bytes=8_197_159,
        embed_dim=1024,
        num_classes=1000,
        trained_on="ImageNet-1k, 1000 classes",
    ),
    _entry(
        head_type_id=_SEGMENTER,
        backbone_id="dinov2-large",
        model="vitl14",
        suffix="ade20k_linear_head",
        sha256="59137f319d7e83c79f3253ab7bf63041f1f884e54ba865a2c7ef0046655306a0",
        size_bytes=1_892_153,
        embed_dim=1024,
        num_classes=150,
        trained_on="ADE20k, 150 classes",
    ),
    _entry(
        head_type_id=_DEPTH,
        backbone_id="dinov2-large",
        model="vitl14",
        suffix="nyu_linear_head",
        sha256="a853f7dcea0c1e1243cb21b4629b8c61787be9bda51b1f22678aeb8307d82cbf",
        size_bytes=6_299_371,
        embed_dim=1024,
        num_classes=None,
        trained_on="NYU Depth v2",
        depth_range=_NYU_RANGE,
    ),
)

#: Read-only view: nothing mutates the catalogue after import.
CATALOG: MappingProxyType[str, CatalogEntry] = MappingProxyType(
    {entry.id: entry for entry in _ENTRIES}
)


def all_catalog_entries() -> tuple[CatalogEntry, ...]:
    """Every entry, in display order."""
    return _ENTRIES


def get_catalog_entry(entry_id: str) -> CatalogEntry | None:
    """Look up an entry. Returns None for anything not in the table."""
    return CATALOG.get(entry_id)


def catalog_entries_for_backbone(backbone_id: str) -> tuple[CatalogEntry, ...]:
    """Every default head available for one backbone. Empty for DINOv3, by design."""
    return tuple(entry for entry in _ENTRIES if entry.backbone_id == backbone_id)
