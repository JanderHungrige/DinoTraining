"""Tests for installing a pinned first-party head — the trusted half of doc 15.

The two that matter most: nothing is downloaded before the backbone is checked, and no
`.pth` survives the install. The second is what lets doc 12 claim the head loader has no
pickle branch at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import torch

from app.core.config import Settings
from app.ml.errors import ModelNotInstalledError
from app.ml.heads.catalog import CatalogEntry, get_catalog_entry
from app.ml.heads.install import install_catalog_entry
from app.ml.heads.store import HeadInstanceStore
from tests.head_testkit import install_fake_backbone, upstream_depth, upstream_segmenter

DEPTH_ENTRY = "dinov2-linear-depth-nyu.dinov2-small"
SEG_ENTRY = "dinov2-linear-segmenter-ade20k.dinov2-small"
EMBED = 384


def require_entry(entry_id: str) -> CatalogEntry:
    entry = get_catalog_entry(entry_id)
    assert entry is not None, entry_id
    return entry


def patch_download(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, torch.Tensor]
) -> dict[str, Path]:
    """Stand in for the real fetch with a checkpoint of the true upstream layout.

    The digest check is stubbed because the payload is synthetic; the ordering of that
    check against the load is covered directly in test_head_convert.py.
    """
    seen: dict[str, Path] = {}

    def fake_download(entry: CatalogEntry, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        torch.save(payload, destination)
        seen["path"] = destination
        return destination

    monkeypatch.setattr("app.ml.heads.install.download_entry", fake_download)
    # Patched where it is defined: load_verified_state_dict calls it internally, so
    # patching an install-module alias would miss the call that actually happens.
    monkeypatch.setattr(
        "app.ml.heads.convert.verify_digest", lambda path, expected: expected
    )
    return seen


class TestGuards:
    def test_unknown_entry_raises(self, head_settings: Settings) -> None:
        with pytest.raises(LookupError):
            install_catalog_entry("not-a-real.entry", settings=head_settings)

    def test_backbone_is_checked_before_download(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def explode(entry: CatalogEntry, destination: Path) -> Path:
            raise AssertionError("Must not download before checking the backbone")

        monkeypatch.setattr("app.ml.heads.install.download_entry", explode)

        with pytest.raises(ModelNotInstalledError):
            install_catalog_entry(DEPTH_ENTRY, settings=head_settings)


class TestInstall:
    def test_registers_with_pinned_provenance(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        install_fake_backbone(head_settings, "dinov2-small", EMBED)
        entry = require_entry(DEPTH_ENTRY)
        patch_download(monkeypatch, upstream_depth(EMBED))

        instance = install_catalog_entry(entry.id, settings=head_settings)

        assert instance.kind == "pretrained-default"
        assert instance.task == "depth"
        assert instance.head_type_id == "dinov2-linear-depth-nyu"
        assert instance.backbone_id == "dinov2-small"
        assert instance.embed_dim == EMBED
        # The upstream project, not the file URL — see test_summary_never_shows_a_url.
        assert instance.source_repo == "facebookresearch/dinov2"
        assert instance.source_digest == entry.sha256
        # The exact URL stays auditable in config, where no picker renders it.
        assert instance.config["source_url"] == entry.url
        assert instance.config["catalog_entry_id"] == entry.id
        assert instance.config["trained_on"] == entry.trained_on

    def test_the_pickle_is_deleted_after_conversion(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        install_fake_backbone(head_settings, "dinov2-small", EMBED)
        seen = patch_download(monkeypatch, upstream_depth(EMBED))

        install_catalog_entry(DEPTH_ENTRY, settings=head_settings)

        assert not seen["path"].exists(), "a .pth survived the install"

    def test_segmentation_head_records_its_class_count(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        install_fake_backbone(head_settings, "dinov2-small", EMBED)
        patch_download(monkeypatch, upstream_segmenter(EMBED))

        instance = install_catalog_entry(SEG_ENTRY, settings=head_settings)

        assert instance.num_classes == 150
        listed = HeadInstanceStore(head_settings).list_all(task="segmentation")
        assert [item.id for item in listed] == [instance.id]

    def test_installed_head_summarises_without_a_filename(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Doc 12's cross-tab contract: Waves 3/4 must never see a path."""
        install_fake_backbone(head_settings, "dinov2-small", EMBED)
        patch_download(monkeypatch, upstream_segmenter(EMBED))

        instance = install_catalog_entry(SEG_ENTRY, settings=head_settings)

        assert "Segmentation" in instance.summary
        assert "pretrained default" in instance.summary
        assert ".safetensors" not in instance.summary

    def test_summary_never_shows_a_url_or_filename(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression: the first real install rendered the .pth URL in every picker.

        The earlier assertion only excluded ".safetensors", so a source_repo holding
        the upstream ".pth" download URL passed the suite and was caught only by an
        integration run. Any file extension or scheme in the summary is the bug.
        """
        install_fake_backbone(head_settings, "dinov2-small", EMBED)
        patch_download(monkeypatch, upstream_depth(EMBED))

        instance = install_catalog_entry(DEPTH_ENTRY, settings=head_settings)

        # Not "/" — that is legitimate in the owner/name form the summary should show.
        for fragment in ("http://", "https://", ".pth", ".pt", ".safetensors"):
            assert fragment not in instance.summary, (
                f"{fragment!r} leaked into the cross-tab summary: {instance.summary}"
            )

    def test_name_is_not_double_parenthesised(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Also from the integration run: "… (NYUd) (NYU Depth v2)" read as a glitch."""
        install_fake_backbone(head_settings, "dinov2-small", EMBED)
        patch_download(monkeypatch, upstream_depth(EMBED))

        instance = install_catalog_entry(DEPTH_ENTRY, settings=head_settings)
        assert instance.name.count("(") <= 1

    def test_weights_round_trip_through_the_store(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The stored safetensors must load back into the head it was built for."""
        install_fake_backbone(head_settings, "dinov2-small", EMBED)
        payload = upstream_depth(EMBED)
        patch_download(monkeypatch, payload)

        instance = install_catalog_entry(DEPTH_ENTRY, settings=head_settings)
        loaded = HeadInstanceStore(head_settings).load_weights(instance.id)

        assert set(loaded) == {"conv_depth.weight", "conv_depth.bias"}
        assert torch.allclose(
            loaded["conv_depth.weight"], payload["decode_head.conv_depth.weight"]
        )

    def test_a_second_install_is_rejected(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Silently creating a duplicate would put two identical rows in every picker."""
        install_fake_backbone(head_settings, "dinov2-small", EMBED)
        patch_download(monkeypatch, upstream_depth(EMBED))

        install_catalog_entry(DEPTH_ENTRY, settings=head_settings)
        with pytest.raises(FileExistsError):
            install_catalog_entry(DEPTH_ENTRY, settings=head_settings)
