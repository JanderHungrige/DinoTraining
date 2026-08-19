"""Tests for the mask annotator catalogue.

The catalogue's job is to make the *difference* between the two annotators data rather than
control flow, so the tests assert the properties consumers rely on — that every named model
exists, that sizes are summed across a multi-model annotator, and that the gated/access
distinction is preserved — rather than restating the literal table.
"""

from __future__ import annotations

import pytest

from app.ml.annotators import GROUNDED_SAM, SAM3, all_annotators, get_annotator
from app.ml.registry import get_model


class TestCatalogue:
    def test_both_annotators_are_present(self) -> None:
        assert {spec.id for spec in all_annotators()} == {GROUNDED_SAM, SAM3}

    def test_the_ungated_option_is_listed_first(self) -> None:
        """Display order is catalogue order; a new user should meet the open option first."""
        assert all_annotators()[0].id == GROUNDED_SAM

    def test_every_named_model_exists_in_the_model_catalogue(self) -> None:
        """A typo here is a 500 at run time, and nothing else would catch it."""
        for spec in all_annotators():
            for model_id in spec.model_ids:
                assert get_model(model_id) is not None, f"{spec.id} names unknown {model_id}"

    def test_an_unknown_annotator_id_returns_none(self) -> None:
        assert get_annotator("not-an-annotator") is None

    def test_specs_are_immutable(self) -> None:
        spec = get_annotator(GROUNDED_SAM)
        assert spec is not None
        with pytest.raises((AttributeError, TypeError)):
            spec.licence = "MIT"  # type: ignore[misc]


class TestGroundedSam:
    def test_it_needs_a_detector_and_a_segmenter(self) -> None:
        spec = get_annotator(GROUNDED_SAM)
        assert spec is not None
        kinds = [model.kind for model in spec.models]
        assert "detector" in kinds and "segmenter" in kinds

    def test_it_is_ungated_and_needs_no_access_request(self) -> None:
        """The whole reason it exists: segmentation with no account and no approval."""
        spec = get_annotator(GROUNDED_SAM)
        assert spec is not None
        assert spec.gated is False
        assert spec.requires_access_request is False
        assert all(model.gated is False for model in spec.models)

    def test_its_size_is_the_sum_of_its_models(self) -> None:
        spec = get_annotator(GROUNDED_SAM)
        assert spec is not None
        assert spec.approx_size_mb == sum(model.approx_size_mb for model in spec.models)

    def test_it_is_permissively_licensed(self) -> None:
        spec = get_annotator(GROUNDED_SAM)
        assert spec is not None
        assert spec.licence == "Apache-2.0"


class TestSam3:
    def test_it_is_gated_and_also_needs_an_access_request(self) -> None:
        """The distinction from DINOv3: a token alone is not enough."""
        spec = get_annotator(SAM3)
        assert spec is not None
        assert spec.gated is True
        assert spec.requires_access_request is True

    def test_dinov3_is_gated_but_needs_no_access_request(self) -> None:
        """Pins the contrast — collapsing these two produces a very confusing 403."""
        model = get_model("dinov3-vitb16")
        assert model is not None
        assert model.gated is True
        assert model.requires_access_request is False

    def test_it_is_not_advertised_as_permissive(self) -> None:
        spec = get_annotator(SAM3)
        assert spec is not None
        assert "Apache" not in spec.licence
        assert "MIT" not in spec.licence

    def test_its_licence_url_points_at_its_own_repo(self) -> None:
        """A user sent to the wrong model's page accepts a licence and still gets a 403."""
        spec = get_annotator(SAM3)
        assert spec is not None
        assert spec.licence_url.endswith("facebook/sam3")
