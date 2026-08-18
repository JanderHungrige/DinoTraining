"""Tests for the pinned first-party head catalogue.

Every invariant here is one that, if broken, produces a head that either refuses to
install or installs and predicts nonsense. The digest and shape assertions are the
ones that matter: they are what let a pickle be read at all.
"""

from __future__ import annotations

import re

from app.ml.heads.catalog import (
    CATALOG,
    PINNED_HOST,
    CatalogEntry,
    all_catalog_entries,
    catalog_entries_for_backbone,
    get_catalog_entry,
)
from app.ml.heads.registry import get_head_type
from app.ml.registry import get_model

SHA256 = re.compile(r"^[0-9a-f]{64}$")

#: What each backbone's config.json reports as hidden_size. The catalogue must agree,
#: because a head file is per backbone width and the wrong pairing will not load.
EXPECTED_EMBED_DIM = {"dinov2-small": 384, "dinov2-base": 768, "dinov2-large": 1024}


class TestTableShape:
    def test_nine_entries_three_tasks_by_three_backbones(self) -> None:
        assert len(all_catalog_entries()) == 9

    def test_ids_are_unique(self) -> None:
        ids = [entry.id for entry in all_catalog_entries()]
        assert len(ids) == len(set(ids))

    def test_keys_match_entry_ids(self) -> None:
        assert all(key == entry.id for key, entry in CATALOG.items())

    def test_id_is_head_type_dot_backbone(self) -> None:
        for entry in all_catalog_entries():
            assert entry.id == f"{entry.head_type_id}.{entry.backbone_id}"

    def test_unknown_entry_returns_none(self) -> None:
        assert get_catalog_entry("not-a-head.not-a-backbone") is None

    def test_every_task_is_covered(self) -> None:
        tasks = set()
        for entry in all_catalog_entries():
            spec = get_head_type(entry.head_type_id)
            assert spec is not None
            tasks.add(spec.task)
        assert tasks == {"classification", "segmentation", "depth"}


class TestReferentialIntegrity:
    def test_every_head_type_id_resolves(self) -> None:
        """A typo here is a 500 at install time, not a startup failure."""
        for entry in all_catalog_entries():
            assert get_head_type(entry.head_type_id) is not None, entry.id

    def test_every_backbone_id_resolves_to_a_backbone(self) -> None:
        for entry in all_catalog_entries():
            spec = get_model(entry.backbone_id)
            assert spec is not None, entry.id
            assert spec.kind == "backbone", entry.id

    def test_embed_dim_matches_the_backbone(self) -> None:
        for entry in all_catalog_entries():
            assert entry.embed_dim == EXPECTED_EMBED_DIM[entry.backbone_id], entry.id

    def test_referenced_head_types_are_not_trainable(self) -> None:
        """A fixed upstream label set cannot be fine-tuned — doc 15."""
        for entry in all_catalog_entries():
            spec = get_head_type(entry.head_type_id)
            assert spec is not None
            assert spec.trainable is False, entry.id


class TestPinning:
    def test_every_digest_is_lowercase_sha256(self) -> None:
        for entry in all_catalog_entries():
            assert SHA256.match(entry.sha256), entry.id

    def test_digests_are_unique(self) -> None:
        """Two entries sharing a digest means a copy-paste error in the table."""
        digests = [entry.sha256 for entry in all_catalog_entries()]
        assert len(digests) == len(set(digests))

    def test_urls_are_https_on_the_pinned_host(self) -> None:
        for entry in all_catalog_entries():
            assert entry.url.startswith(f"https://{PINNED_HOST}/"), entry.id

    def test_sizes_are_plausible(self) -> None:
        for entry in all_catalog_entries():
            assert 100_000 < entry.size_bytes < 50_000_000, entry.id

    def test_every_entry_is_apache_licensed(self) -> None:
        """The whole reason these can be redistributed as defaults."""
        for entry in all_catalog_entries():
            assert entry.licence == "Apache-2.0", entry.id


class TestDinoV3Absence:
    def test_no_dinov3_entries(self) -> None:
        """Not an oversight: DINOv3 heads are ViT-7B only, gated, non-redistributable.

        Doc 15 records the research. This test exists so that adding a DINOv3 entry
        without revisiting that decision fails loudly.
        """
        for entry in all_catalog_entries():
            spec = get_model(entry.backbone_id)
            assert spec is not None
            assert spec.family == "dinov2", entry.id


class TestFiltering:
    def test_entries_for_a_backbone(self) -> None:
        found = catalog_entries_for_backbone("dinov2-small")
        assert len(found) == 3
        assert all(entry.backbone_id == "dinov2-small" for entry in found)

    def test_entries_for_a_backbone_with_no_heads(self) -> None:
        assert catalog_entries_for_backbone("dinov3-vitb16") == ()


class TestDepthRange:
    def test_only_depth_entries_carry_a_range(self) -> None:
        for entry in all_catalog_entries():
            spec = get_head_type(entry.head_type_id)
            assert spec is not None
            if spec.task == "depth":
                assert entry.depth_range == (0.001, 10.0), entry.id
            else:
                assert entry.depth_range is None, entry.id


class TestImmutability:
    def test_entries_are_frozen(self) -> None:
        entry: CatalogEntry = all_catalog_entries()[0]
        try:
            entry.sha256 = "0" * 64  # type: ignore[misc]
        except (AttributeError, TypeError):
            return
        raise AssertionError("CatalogEntry must be immutable — a mutable digest is not a pin")
