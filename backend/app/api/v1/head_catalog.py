"""The head catalogue and the community-import door.

Status codes are load-bearing here, because the UI branches on them and each one maps
to a different fix for the user:

* ``409`` — do something first (download the backbone; it is already installed)
* ``415`` — this repo will never work (pickles only)
* ``422`` — these bytes are wrong (digest mismatch, or shapes that do not fit)
* ``503`` — upstream is down; try again later

Collapsing them into a blanket 400 would tell the user "something went wrong" for four
situations with four different remedies.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.v1.heads import HeadInstanceInfo, describe_instance
from app.ml.backbone import BackboneCapabilities, read_capabilities
from app.ml.errors import ModelNotInstalledError
from app.ml.heads.catalog import CatalogEntry, all_catalog_entries
from app.ml.heads.convert import (
    DigestMismatchError,
    UnsupportedCheckpointError,
    UpstreamUnavailableError,
)
from app.ml.heads.importer import (
    InvalidRepoIdError,
    PickleRefusedError,
    import_community_head,
)
from app.ml.heads.install import install_catalog_entry
from app.ml.heads.instances import HeadInstance
from app.ml.heads.register import IncompatibleHeadError
from app.ml.heads.registry import HeadTypeSpec, check_compatibility, get_head_type
from app.ml.heads.store import HeadInstanceStore
from app.ml.registry import get_model

logger = logging.getLogger(__name__)
router = APIRouter()


class CatalogEntryInfo(BaseModel):
    id: str
    title: str
    task: str
    head_type_id: str
    backbone_id: str
    trained_on: str = Field(description="Provenance — the dataset and its class count.")
    licence: str
    size_bytes: int
    num_classes: int | None
    installed: bool
    installed_instance_id: str | None
    backbone_installed: bool = Field(
        description="False means the entry cannot be installed until the backbone is."
    )
    compatible: bool | None = Field(default=None, description="Null unless ?backbone= given.")
    incompatible_reason: str | None = None


class CatalogListResponse(BaseModel):
    entries: list[CatalogEntryInfo]


class ImportRequest(BaseModel):
    repo_id: str = Field(description="HuggingFace repo id, owner/name. Safetensors only.")
    head_type_id: str
    backbone_id: str
    num_classes: int | None = None
    name: str | None = None


def _title(entry: CatalogEntry) -> str:
    """Compose from the head-type spec so the table cannot drift from the registry."""
    spec = get_head_type(entry.head_type_id)
    return spec.title if spec is not None else entry.head_type_id


def _installed_index(entries: tuple[CatalogEntry, ...]) -> dict[str, HeadInstance]:
    """Map catalogue id -> the instance installed from it, if any.

    Read through ``list_all`` — doc 12's contract — rather than by probing the heads
    directory, so "installed" means the same thing here as in every picker.
    """
    installed = HeadInstanceStore().list_all()
    by_key = {
        (item.head_type_id, item.backbone_id): item
        for item in installed
        if item.kind == "pretrained-default"
    }
    found: dict[str, HeadInstance] = {}
    for entry in entries:
        match = by_key.get((entry.head_type_id, entry.backbone_id))
        if match is not None:
            found[entry.id] = match
    return found


def _resolve_backbone(backbone: str) -> BackboneCapabilities | None:
    """Capabilities for a backbone, or None when it is not installed.

    An uninstalled backbone is not an error for the *list* endpoint: the user needs to
    see the catalogue in order to decide which backbone to download.
    """
    if get_model(backbone) is None:
        raise HTTPException(status_code=404, detail=f"Unknown backbone: {backbone}")
    try:
        return read_capabilities(backbone)
    except ModelNotInstalledError:
        return None
    except (LookupError, ValueError) as exc:
        logger.warning("Cannot read capabilities for %s: %s", backbone, exc)
        return None


def _verdict(
    entry: CatalogEntry, spec: HeadTypeSpec, capabilities: BackboneCapabilities
) -> tuple[bool, str | None]:
    """Can this entry be installed against the backbone the user asked about?

    Every entry gets an answer, not just the ones matching the backbone. A head built
    for another backbone size *is* unusable with the current selection, and the wave
    rule is to say why rather than leave the row unexplained — the user's next move
    ("download dinov2-base") depends on being told which backbone it needs.

    The family check runs first because its message is the more informative one: for a
    DINOv3 selection, "no DINOv2 head fits this" beats "this head wants dinov2-small".
    """
    family = check_compatibility(spec, capabilities)
    if not family.compatible:
        return False, family.reason

    if entry.backbone_id != capabilities.model_id:
        return False, (
            f"This head was trained for {entry.backbone_id} "
            f"(embed_dim {entry.embed_dim}), but you selected {capabilities.model_id} "
            f"(embed_dim {capabilities.embed_dim}). Install the {entry.backbone_id} "
            "head for this backbone instead."
        )

    if entry.embed_dim != capabilities.embed_dim:
        # Defensive: a backbone whose config disagrees with the pinned table means the
        # catalogue is stale, and installing would fail later with a shape error.
        return False, (
            f"{entry.backbone_id} reports embed_dim {capabilities.embed_dim}, but this "
            f"head expects {entry.embed_dim}. The catalogue entry is out of date."
        )

    return True, None


def _describe(
    entry: CatalogEntry,
    installed: dict[str, HeadInstance],
    capabilities: BackboneCapabilities | None,
    requested_backbone: str | None,
) -> CatalogEntryInfo:
    spec = get_head_type(entry.head_type_id)
    instance = installed.get(entry.id)

    compatible: bool | None = None
    reason: str | None = None
    if capabilities is not None and spec is not None:
        compatible, reason = _verdict(entry, spec, capabilities)

    return CatalogEntryInfo(
        id=entry.id,
        title=_title(entry),
        task=spec.task if spec is not None else "unknown",
        head_type_id=entry.head_type_id,
        backbone_id=entry.backbone_id,
        trained_on=entry.trained_on,
        licence=entry.licence,
        size_bytes=entry.size_bytes,
        num_classes=entry.num_classes,
        installed=instance is not None,
        installed_instance_id=instance.id if instance is not None else None,
        backbone_installed=_is_backbone_installed(entry.backbone_id),
        compatible=compatible,
        incompatible_reason=reason,
    )


def _is_backbone_installed(backbone_id: str) -> bool:
    from app.core.paths import is_installed, resolve_model_dir

    return is_installed(resolve_model_dir(backbone_id))


@router.get(
    "/head-catalog",
    response_model=CatalogListResponse,
    summary="List downloadable first-party heads",
)
async def list_catalog(
    backbone: str | None = Query(
        default=None, description="Registry id of a backbone to check compatibility against."
    ),
) -> CatalogListResponse:
    entries = all_catalog_entries()
    capabilities = _resolve_backbone(backbone) if backbone is not None else None
    installed = _installed_index(entries)
    return CatalogListResponse(
        entries=[_describe(entry, installed, capabilities, backbone) for entry in entries]
    )


@router.post(
    "/head-catalog/{entry_id}/install",
    response_model=HeadInstanceInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Download, verify and install a pinned default head",
)
async def install_entry(entry_id: str) -> HeadInstanceInfo:
    try:
        return describe_instance(install_catalog_entry(entry_id))
    # ModelNotInstalledError subclasses LookupError, so it must be caught first —
    # otherwise "download the backbone" (409) is reported as "unknown entry" (404).
    except ModelNotInstalledError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} is not installed — download the backbone first.",
        ) from None
    except LookupError:
        raise HTTPException(
            status_code=404, detail=f"Unknown catalogue entry: {entry_id}"
        ) from None
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except (DigestMismatchError, UnsupportedCheckpointError, IncompatibleHeadError) as exc:
        # 422, not 500: the request was well-formed, the *bytes* did not check out.
        logger.error("Install rejected for %s: %s", entry_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except UpstreamUnavailableError as exc:
        logger.warning("Upstream unavailable for %s: %s", entry_id, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.post(
    "/heads/import",
    response_model=HeadInstanceInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Import a community head from a HuggingFace repo (safetensors only)",
)
async def import_head(request: ImportRequest) -> HeadInstanceInfo:
    try:
        instance = import_community_head(
            repo_id=request.repo_id,
            head_type_id=request.head_type_id,
            backbone_id=request.backbone_id,
            num_classes=request.num_classes,
            name=request.name,
        )
    except InvalidRepoIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except PickleRefusedError as exc:
        # 415: the request is fine, the repository's format is not — and no retry or
        # parameter change on the caller's side will alter that.
        raise HTTPException(status_code=415, detail=str(exc)) from None
    # Before the bare LookupError below, which it subclasses.
    except ModelNotInstalledError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} is not installed — download the backbone first.",
        ) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except IncompatibleHeadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except ValueError as exc:
        # Backstop. Everything downstream validates untrusted input by raising
        # ValueError, and one that escapes reaches the user as an opaque 500 with the
        # reason buried in the log — which is how the missing class count first showed
        # up. Anything that gets here is still a rejected *input*, so 422 is right.
        logger.error("Import rejected for %s: %s", request.repo_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return describe_instance(instance)
