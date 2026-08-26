"""Names for a pretrained head's classes.

Reported as "the DINOv2 linear classifier gives class 705, class 547". Both are real
answers — `passenger car, coach, carriage` and `electric locomotive` — so on rail images
the model was right and could not say so.

The risk in a label list is not that it is missing. It is that it is **present and wrong**:
a set one entry short, or applied to the wrong head, names every class after the shift
with a neighbour's name, and `electric locomotive` on a passenger car is exactly as
plausible as the truth. So most of these tests are about refusing to guess.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ml.heads.labels import (
    ADE20K,
    IMAGENET_1K,
    LABEL_SETS,
    label_names,
    names_for,
)
from app.ml.heads.registry import all_head_types, get_head_type


class TestTheVendoredSets:
    def test_imagenet_has_a_thousand_names(self) -> None:
        assert len(label_names(IMAGENET_1K)) == 1000

    def test_ade20k_has_a_hundred_and_fifty(self) -> None:
        assert len(label_names(ADE20K)) == 150

    def test_the_reported_indices_resolve(self) -> None:
        """The two from the report, and the one the RF-DETR loader's comment names."""
        names = label_names(IMAGENET_1K)
        assert names[705] == "passenger car, coach, carriage"
        assert names[547] == "electric locomotive"
        assert names[416] == "balance beam, beam"

    def test_ade20k_class_zero_is_wall(self) -> None:
        """`overlays/registry.tsx` dims class 0 only when it is *named* background, and
        ADE20k's is not — it is a real prediction. A label set in the other common ADE20k
        order (background first, 151 entries) would shift every class by one and make that
        comment false without changing a line of it."""
        assert label_names(ADE20K)[0] == "wall"

    def test_no_name_is_blank(self) -> None:
        # A blank renders as an empty legend entry, which reads as a rendering bug.
        for label_set in LABEL_SETS:
            assert all(name.strip() for name in label_names(label_set))

    def test_every_set_records_where_it_came_from(self) -> None:
        """The question a reader has in a year is "can I trust this order?", and the answer
        has to travel with the data rather than living in a commit message."""
        directory = Path(__file__).resolve().parents[1] / "app" / "ml" / "heads" / "labels"
        for label_set in LABEL_SETS:
            payload = json.loads((directory / f"{label_set}.json").read_text(encoding="utf-8"))
            assert payload["source_repo"]
            assert payload["note"]

    def test_an_unknown_set_is_empty_not_an_error(self) -> None:
        # Names are a display nicety. A head must never fail to load over them.
        assert label_names("not-a-label-set") == ()


class TestItRefusesToGuess:
    def test_a_mismatched_count_is_refused(self) -> None:
        """The failure this exists to prevent. Applying a 1000-name set to a 999-class head
        names every class after the gap with its neighbour's name — wrong, and plausible."""
        assert names_for(IMAGENET_1K, 999) == ()

    def test_the_exact_count_is_applied(self) -> None:
        assert len(names_for(IMAGENET_1K, 1000)) == 1000

    def test_no_label_set_means_no_names(self) -> None:
        # A trained head's classes are the user's, recorded at save time.
        assert names_for(None, 1000) == ()

    def test_a_head_type_declares_its_set_rather_than_it_being_inferred(self) -> None:
        """1000 classes does not mean ImageNet and 150 does not mean ADE20k. Inferring from
        the count would give the next 150-class head ADE20k's names, every one wrong."""
        classifier = get_head_type("dinov2-linear-classifier-in1k")
        segmenter = get_head_type("dinov2-linear-segmenter-ade20k")
        assert classifier is not None and segmenter is not None
        assert classifier.label_set == IMAGENET_1K
        assert segmenter.label_set == ADE20K

    def test_a_trainable_head_has_no_label_set(self) -> None:
        for spec in all_head_types():
            if spec.trainable:
                assert spec.label_set is None, f"{spec.id} would overwrite the user's classes"

    def test_the_depth_head_has_none_either(self) -> None:
        # Depth predicts metres, not classes. A label set here would be meaningless.
        spec = get_head_type("dinov2-linear-depth-nyu")
        assert spec is not None and spec.label_set is None

    def test_every_declared_set_exists_and_fits(self) -> None:
        """A head type naming a set that is missing, or one of the wrong size, is a
        packaging error that would otherwise show up as bare indices in the viewer."""
        for spec in all_head_types():
            if spec.label_set is None:
                continue
            assert label_names(spec.label_set), f"{spec.id} names a missing set"


class TestExistingInstallsAreFixedToo:
    """The half that decides whether the report is actually answered.

    The reporter already had the classifier installed, and its stored `class_names` is an
    empty list. Filling names only at registration would leave every existing install
    showing `class 705` until it was removed and downloaded again.
    """

    def test_a_stored_empty_list_resolves_through_the_registry(self) -> None:
        from app.ml.heads.store import _stored_class_names

        names = _stored_class_names("dinov2-linear-classifier-in1k", 1000, "[]")
        assert names[705] == "passenger car, coach, carriage"

    def test_recorded_names_always_win(self) -> None:
        """A head trained here carries the user's own classes. A head type that gains a
        label set later must never overwrite them."""
        from app.ml.heads.store import _stored_class_names

        stored = json.dumps(["bolt", "nut"])
        assert _stored_class_names("linear-classifier", 2, stored) == ("bolt", "nut")

    def test_an_unknown_head_type_yields_no_names(self) -> None:
        from app.ml.heads.store import _stored_class_names

        assert _stored_class_names("not-a-head-type", 10, "[]") == ()

    def test_a_count_that_no_longer_matches_is_refused(self) -> None:
        """A head registered with a different class count than its type's label set — from
        an import, or from an upstream change — keeps its indices rather than being
        mislabelled."""
        from app.ml.heads.store import _stored_class_names

        assert _stored_class_names("dinov2-linear-classifier-in1k", 42, "[]") == ()


@pytest.mark.parametrize("label_set", LABEL_SETS)
def test_names_are_cached_rather_than_reread(label_set: str) -> None:
    """1000 entries, read once per head registration and once per prediction payload."""
    assert label_names(label_set) is label_names(label_set)
