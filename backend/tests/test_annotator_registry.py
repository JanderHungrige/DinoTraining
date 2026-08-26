"""Tests for the mask annotator catalogue.

The catalogue's job is to make the *difference* between annotators data rather than control
flow, so the tests assert the properties consumers rely on — that every named model exists,
that sizes are summed across a multi-model annotator, and that the gated/access distinction
is preserved — rather than restating the literal table.

Since doc 27's update, Grounded SAM is three rows rather than one, which turns several of
these into properties that must hold for *every* tier. Written that way on purpose: a
fourth size should need no edit here, and any assertion that only holds for the default one
is a test that would pass while the new tiers were broken.
"""

from __future__ import annotations

import pytest

from app.ml.annotators import GROUNDED_SAM, SAM3, all_annotators, get_annotator
from app.ml.annotators.registry import GROUNDED_SAM_BASE, GROUNDED_SAM_LARGE
from app.ml.registry import all_models, get_model

#: Every ungated tier of the pipeline. Kept as a fixture-free tuple so each test below can
#: state which of them it means.
GROUNDED_TIERS = (GROUNDED_SAM, GROUNDED_SAM_BASE, GROUNDED_SAM_LARGE)


class TestCatalogue:
    def test_every_annotator_is_present(self) -> None:
        assert {spec.id for spec in all_annotators()} == {*GROUNDED_TIERS, SAM3}

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


class TestTheGroundedSamTiers:
    """Three sizes of one pipeline (doc 27).

    The risk in a variant is not that it fails — it is that it *works* while running the
    wrong weights, or reports itself as another tier. Nothing downstream would notice.
    """

    @pytest.mark.parametrize("annotator_id", GROUNDED_TIERS)
    def test_every_tier_pairs_a_detector_with_a_segmenter(self, annotator_id: str) -> None:
        spec = get_annotator(annotator_id)
        assert spec is not None
        kinds = [model.kind for model in spec.models]
        assert kinds == ["detector", "segmenter"], f"{annotator_id} is not detector→segmenter"

    def test_the_tiers_name_different_weights(self) -> None:
        """Otherwise it is three names for one pipeline, which is worse than one name."""
        combinations = {get_annotator(tier).model_ids for tier in GROUNDED_TIERS}  # type: ignore[union-attr]
        assert len(combinations) == len(GROUNDED_TIERS)

    def test_they_are_ordered_smallest_first(self) -> None:
        """Catalogue order is display order, and the default is the one in the starter set.
        A picker that opens on a 1.7 GB download nobody has installed is a dead end."""
        sizes = [get_annotator(tier).approx_size_mb for tier in GROUNDED_TIERS]  # type: ignore[union-attr]
        assert sizes == sorted(sizes)

    def test_the_default_tier_is_the_one_the_starter_set_installs(self) -> None:
        """The link between doc 65 and this doc. If the starter set stops covering the
        default tier, a fresh install offers a pipeline it cannot run."""
        spec = get_annotator(GROUNDED_SAM)
        assert spec is not None
        assert all(get_model(model_id).starter for model_id in spec.model_ids)  # type: ignore[union-attr]

    @pytest.mark.parametrize("annotator_id", GROUNDED_TIERS)
    def test_no_tier_is_gated(self, annotator_id: str) -> None:
        """The reason the pipeline exists at all: masks with no account and no approval.
        A bigger half that quietly needed a token would take that away without saying so."""
        spec = get_annotator(annotator_id)
        assert spec is not None
        assert spec.gated is False
        assert spec.requires_access_request is False
        assert all(model.gated is False for model in spec.models)
        assert spec.licence == "Apache-2.0"

    def test_there_is_no_larger_detector_to_offer(self) -> None:
        """Pins *why* the large tier differs from base on the SAM half alone: IDEA-Research
        published tiny and base as open weights and nothing bigger. If a larger one is ever
        added to the catalogue, this fails and the large tier should be revisited."""
        catalogued = {spec.id for spec in all_models() if spec.family == "grounding-dino"}
        assert catalogued == {"grounding-dino-tiny", "grounding-dino-base"}

    @pytest.mark.parametrize("annotator_id", GROUNDED_TIERS)
    def test_every_tier_takes_several_phrases(self, annotator_id: str) -> None:
        """`prompt_style` replaced an `annotator_id == GROUNDED_SAM` in the UI. That
        comparison was silently right for one row and wrong for these two."""
        spec = get_annotator(annotator_id)
        assert spec is not None
        assert spec.prompt_style == "phrases"

    def test_sam3_takes_one_concept(self) -> None:
        spec = get_annotator(SAM3)
        assert spec is not None
        assert spec.prompt_style == "concept"


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
