"""Fine-tuned models are listed and built as what they are (docs 94, 95)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.finetune.adapters import get_adapter
from app.finetune.adapters.backbone import BackboneAdapter
from app.main import create_app
from app.ml.foundation.build import _trained_spec
from app.ml.foundation.instances import FoundationInstanceStore


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_connection()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_connection()
    get_settings.cache_clear()


def _save(kind: str, finetune_id: str, base: str) -> str:
    return (
        FoundationInstanceStore()
        .save(
            existing_id=None,
            name="mine",
            base_model_id=base,
            dataset_ids=("d",),
            class_names=("ring",),
            metrics={"miou": 0.9},
            epochs_trained=3,
            save=lambda directory: None,
            finetune_id=finetune_id,
            weights_kind=kind,
        )
        .id
    )


def test_every_dino_backbone_and_task_has_its_adapter() -> None:
    adapter = get_adapter("dinov3-vitb16-classification")
    assert isinstance(adapter, BackboneAdapter)
    assert (adapter.backbone_id, adapter.spec.task, adapter.primary_metric) == (
        "dinov3-vitb16",
        "classification",
        adapter.spec.primary_metric,
    )
    assert get_adapter("dinov2-small-segmentation").spec.id == "linear-segmenter"  # type: ignore[attr-defined]


def test_a_backbone_variant_is_its_own_model_with_its_own_head(client: TestClient) -> None:
    # Doc 55's lesson: a head trained on the base must never run on the variant, so the
    # variant is listed and built under its own id, with the head trained alongside it.
    instance_id = _save("backbone-variant", "dinov2-small-segmentation", "dinov2-small")
    spec = _trained_spec(instance_id, None)
    assert spec is not None
    assert (spec.variant_head_type, spec.task, spec.render_hint) == (
        "linear-segmenter",
        "segmentation",
        "masks",
    )
    listed = {f["id"]: f for f in client.get("/api/v1/foundation").json()["foundations"]}
    assert (listed[instance_id]["task"], listed[instance_id]["render_hint"]) == (
        "segmentation",
        "masks",
    )


def test_a_fine_tuned_sam_is_listed_as_grounded_sam_with_it(client: TestClient) -> None:
    instance_id = _save("sam-mask-decoder", "sam2.1-hiera-small", "sam2.1-hiera-small")
    spec = _trained_spec(instance_id, None)
    assert spec is not None
    assert (spec.annotator_id, spec.segmenter_id, spec.model_id) == (
        "grounded-sam",
        instance_id,
        "grounding-dino-tiny",
    )
    listed = {f["id"]: f for f in client.get("/api/v1/foundation").json()["foundations"]}
    assert listed[instance_id]["title"] == "Grounded SAM · mine"
    assert listed[instance_id]["takes_concept"] is True
