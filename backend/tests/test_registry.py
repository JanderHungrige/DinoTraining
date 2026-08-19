"""Tests for the model catalogue."""

from __future__ import annotations

import pytest

from app.ml.registry import MODELS, all_models, get_model, licence_url


class TestRegistry:
    def test_ids_are_unique(self) -> None:
        ids = [spec.id for spec in all_models()]
        assert len(ids) == len(set(ids))

    def test_lookup_returns_the_matching_spec(self) -> None:
        spec = get_model("dinov2-base")
        assert spec is not None
        assert spec.repo_id == "facebook/dinov2-base"

    def test_unknown_id_returns_none(self) -> None:
        assert get_model("does-not-exist") is None

    def test_traversal_id_returns_none(self) -> None:
        """The registry lookup is what turns a traversal attempt into a 404."""
        assert get_model("../../etc/passwd") is None

    def test_gated_models_are_exactly_the_custom_licensed_ones(self) -> None:
        """Was `test_only_dinov3_is_gated` until SAM 3 joined it.

        The invariant is not "which ids" but that gating and a non-permissive licence go
        together — an Apache-2.0 entry behind a gate would be a catalogue mistake.
        """
        gated = {spec.id for spec in all_models() if spec.gated}
        assert gated == {"dinov3-vitb16", "dinov3-vitl16", "sam3"}
        for spec in all_models():
            if spec.gated:
                assert spec.licence != "Apache-2.0", f"{spec.id} is gated but Apache-2.0"
            else:
                assert spec.licence == "Apache-2.0", f"{spec.id} is open but not Apache-2.0"

    def test_only_sam3_needs_a_manual_access_request(self) -> None:
        needing = {spec.id for spec in all_models() if spec.requires_access_request}
        assert needing == {"sam3"}

    def test_anything_needing_approval_is_also_gated(self) -> None:
        """An access request without a gate is incoherent, and would skip the token check."""
        for spec in all_models():
            if spec.requires_access_request:
                assert spec.gated

    def test_every_family_has_an_entry(self) -> None:
        families = {spec.family for spec in all_models()}
        assert families == {"grounding-dino", "dinov2", "dinov3", "sam2", "sam3"}

    def test_specs_are_immutable(self) -> None:
        """The catalogue is not user-editable; a frozen dataclass enforces that."""
        import dataclasses

        import pytest

        spec = MODELS["dinov2-base"]
        with pytest.raises(dataclasses.FrozenInstanceError):
            spec.repo_id = "attacker/evil-repo"  # type: ignore[misc]

    def test_every_spec_has_a_plausible_size(self) -> None:
        assert all(spec.approx_size_mb > 0 for spec in all_models())

    def test_every_spec_has_a_description(self) -> None:
        assert all(spec.description.strip() for spec in all_models())


class TestLicenceUrl:
    def test_points_at_the_models_own_repo(self) -> None:
        spec = MODELS["dinov3-vitl16"]
        assert licence_url(spec).endswith(spec.repo_id)

    def test_gated_models_get_distinct_urls(self) -> None:
        """Both DINOv3 cards once linked to the vitb16 gate — accepting it there
        still leaves vitl16 returning 403."""
        gated = [spec for spec in all_models() if spec.gated]
        urls = {licence_url(spec) for spec in gated}
        assert len(urls) == len(gated)


class TestNothingIsBundledOrAutoDownloaded:
    """Weights are never shipped in the installer and never fetched behind the user.

    The catalogue totals ~8 GB and SAM 3 alone is 3.2 GB, so an implicit download is the
    difference between a 30 MB install and an unusable one. Every loader must refuse
    rather than fetch, and the only place that may fetch is the admin-triggered job.
    """

    def test_only_the_download_manager_may_fetch(self) -> None:
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[1] / "app"
        offenders = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*.py")
            if "snapshot_download" in path.read_text(encoding="utf-8")
            and path.name != "downloads.py"
            # paths.py only mentions it in a comment about what it writes.
            and "snapshot_download(" in path.read_text(encoding="utf-8")
        ]
        assert offenders == [], f"implicit download reachable from: {offenders}"

    def test_every_loader_refuses_a_missing_model(
        self, tmp_path: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.core.config import get_settings
        from app.ml.backbone import load_backbone
        from app.ml.detector import load_detector
        from app.ml.errors import ModelNotInstalledError
        from app.ml.segmenter import load_segmenter

        monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path))
        get_settings.cache_clear()
        try:
            for load, model_id in (
                (load_detector, "grounding-dino-tiny"),
                (load_segmenter, "sam2.1-hiera-small"),
                (load_segmenter, "sam3"),
                (load_backbone, "dinov2-small"),
            ):
                with pytest.raises(ModelNotInstalledError):
                    load(model_id)
        finally:
            get_settings.cache_clear()

    def test_the_catalogue_reports_what_a_full_install_would_cost(self) -> None:
        """A sanity bound, so a mis-typed size cannot quietly claim 30 GB or 30 MB."""
        total_gb = sum(spec.approx_size_mb for spec in all_models()) / 1024
        assert 5 < total_gb < 12, f"catalogue total looks wrong: {total_gb:.1f} GB"
