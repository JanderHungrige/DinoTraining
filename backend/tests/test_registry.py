"""Tests for the model catalogue."""

from __future__ import annotations

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
