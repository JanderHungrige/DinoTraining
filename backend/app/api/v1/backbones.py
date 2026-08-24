"""Backbone capabilities for the trainer and head-compatibility checks.

This is the read side of `07-backbone-feature-extractor`: what backbones exist, which
are installed, and — for the installed ones — the descriptor that decides whether a
head fits. Weights are never loaded to answer this.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.paths import is_installed, resolve_model_dir
from app.ml.backbone import read_capabilities
from app.ml.registry import ModelFamily, ModelSpec, all_models

logger = logging.getLogger(__name__)
router = APIRouter()


class Capabilities(BaseModel):
    patch_size: int
    embed_dim: int = Field(description="Head input width — the main compatibility axis.")
    num_prefix_tokens: int = Field(description="1 (CLS) + register tokens, if any.")
    num_layers: int
    image_size: int


class BackboneInfo(BaseModel):
    id: str
    family: ModelFamily
    gated: bool
    installed: bool
    capabilities: Capabilities | None = Field(
        default=None,
        description="Null unless installed — the descriptor is read from the model's config.",
    )


class BackboneListResponse(BaseModel):
    backbones: list[BackboneInfo]


def _describe(spec: ModelSpec) -> BackboneInfo:
    """Catalogue entry plus, when present, the on-disk descriptor."""
    installed = is_installed(resolve_model_dir(spec.id))
    capabilities: Capabilities | None = None

    if installed:
        try:
            caps = read_capabilities(spec.id)
            capabilities = Capabilities(
                patch_size=caps.patch_size,
                embed_dim=caps.embed_dim,
                num_prefix_tokens=caps.num_prefix_tokens,
                num_layers=caps.num_layers,
                image_size=caps.image_size,
            )
        except (ValueError, LookupError) as exc:
            # One corrupt config must not blank the whole list — the user still needs
            # to see their other backbones, and the log carries the real reason.
            logger.warning("Cannot read capabilities for %s: %s", spec.id, exc)

    return BackboneInfo(
        id=spec.id,
        family=spec.family,
        gated=spec.gated,
        installed=installed,
        capabilities=capabilities,
    )


@router.get(
    "/backbones",
    response_model=BackboneListResponse,
    summary="List backbones and their capabilities",
)
async def list_backbones() -> BackboneListResponse:
    return BackboneListResponse(
        backbones=[_describe(spec) for spec in all_models() if spec.kind == "backbone"]
    )
