"""Export bundles (doc 121): what is in the zip, and what never is."""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import torch
from httpx import AsyncClient

from app.ml.foundation.instances import FoundationInstanceStore
from app.ml.heads.store import HeadInstanceStore
from tests.datasets_api_testkit import dataset_client


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


def _head() -> str:
    return (
        HeadInstanceStore()
        .register(
            name="Screws m8/m9",
            kind="trained-here",
            head_type_id="linear-classifier",
            task="classification",
            backbone_id="dinov2-small",
            backbone_family="dinov2",
            embed_dim=384,
            num_classes=2,
            weights={"linear.weight": torch.randn(2, 384), "linear.bias": torch.zeros(2)},
            class_names=("m8", "m9"),
        )
        .id
    )


def _zip(data: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(data))


class TestHeadBundle:
    async def test_download_holds_card_weights_and_readme(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        response = await client.post(
            "/api/v1/exports", json={"kind": "heads", "instance_id": _head()}
        )
        assert response.status_code == 200
        assert 'filename="Screws_m8_m9.zip"' in response.headers["content-disposition"]
        archive = _zip(response.content)
        names = set(archive.namelist())
        assert {"model.json", "head.safetensors", "README.md"} <= names
        card = json.loads(archive.read("model.json"))
        assert card["weights"][0]["file"] == "head.safetensors"
        assert card["classes"] == ["m8", "m9"]
        # No local path anywhere in the bundle (doc 120, rule 3).
        for name in names:
            assert str(tmp_path).encode() not in archive.read(name), name

    async def test_without_an_installed_backbone_there_is_no_runtime_and_it_says_so(
        self, client: AsyncClient
    ) -> None:
        """Preprocessing needs the backbone's config; without it predict.py would guess."""
        response = await client.post(
            "/api/v1/exports", json={"kind": "heads", "instance_id": _head()}
        )
        archive = _zip(response.content)
        assert "dino_runtime.py" not in archive.namelist()
        assert "not covered by the exported runtime" in archive.read("README.md").decode()

    async def test_writes_into_a_folder(self, client: AsyncClient, tmp_path: Path) -> None:
        body = {"kind": "heads", "instance_id": _head(), "destination": str(tmp_path)}
        response = await client.post("/api/v1/exports", json=body)
        assert Path(response.json()["path"]).is_file()

    async def test_a_bad_folder_or_model_is_said_plainly(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        body = {"kind": "heads", "instance_id": _head(), "destination": "relative/folder"}
        assert (await client.post("/api/v1/exports", json=body)).status_code == 422
        missing = await client.post(
            "/api/v1/exports", json={"kind": "heads", "instance_id": "nope"}
        )
        assert missing.status_code == 404

    async def test_location_is_the_folder_holding_it(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        response = await client.get(f"/api/v1/exports/heads/{_head()}/location")
        assert response.json()["folder"] == str(tmp_path / "heads")


class TestFinetunedBundle:
    async def test_pt_weights_become_safetensors_without_running_pickles(
        self, client: AsyncClient
    ) -> None:
        def save(directory: Path) -> None:
            torch.save({"w": torch.ones(2, 2)}, directory / "mask_decoder.pt")

        saved = FoundationInstanceStore().save(
            existing_id=None,
            name="outlines",
            base_model_id="sam2.1-hiera-small",
            dataset_ids=(),
            class_names=("ring",),
            metrics={"miou": 0.9},
            epochs_trained=1,
            save=save,
            weights_kind="sam-mask-decoder",
        )
        response = await client.post(
            "/api/v1/exports", json={"kind": "finetuned", "instance_id": saved.id}
        )
        archive = _zip(response.content)
        assert "mask_decoder.safetensors" in archive.namelist()
        from safetensors.torch import load

        assert torch.equal(load(archive.read("mask_decoder.safetensors"))["w"], torch.ones(2, 2))
        assert (
            json.loads(archive.read("model.json"))["weights"][0]["file"]
            == "mask_decoder.safetensors"
        )
