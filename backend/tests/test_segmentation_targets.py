"""Training a segmentation head on stored masks.

`linear-segmenter` was registered `trainable=True` with a loss and metrics wired to it and
**nothing that could produce the target it reads** — a run raised `KeyError: 'mask'` on the
first batch, and nothing refused it earlier. Doc 61 gave the Studio somewhere to put a
segmentation; this is the path from there to a trained head.

What is worth pinning is not "a tensor comes out" but the four decisions inside it: that
class 0 means background, that an `unclear` region survives a positive claiming it, that
the mask lands exactly where the image landed, and that an unsegmented image is not
mistaken for an empty one.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch
from PIL import Image

from app.datasets.rle import rle_encode
from app.ml.backbone import BackboneCapabilities
from app.ml.heads.registry import get_head_type
from app.ml.preprocess import GeometryTransform, apply_geometry, plan_preprocessing
from app.ml.training.loop import build_targets, segmentation_target
from app.ml.training.losses import IGNORE_INDEX, segmentation_loss
from app.ml.training.samples import (
    BACKGROUND_CLASS,
    MaskTarget,
    SampleSet,
    TrainingSample,
    classes_for_task,
    learnable_classes,
)

WIDTH, HEIGHT = 40, 20


def spec_for(head_id: str):
    found = get_head_type(head_id)
    assert found is not None
    return found


def _capabilities() -> BackboneCapabilities:
    return BackboneCapabilities(
        model_id="dinov2-small",
        family="dinov2",
        patch_size=14,
        embed_dim=384,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )


def rle_for(box: tuple[int, int, int, int]) -> tuple[int, ...]:
    """Column-major run lengths for a filled rectangle."""
    x, y, w, h = box
    array = np.zeros((HEIGHT, WIDTH), dtype=bool)
    array[y : y + h, x : x + w] = True
    return tuple(rle_encode(array)[0])


def mask_target(class_index: int, box: tuple[int, int, int, int]) -> MaskTarget:
    return MaskTarget(class_index=class_index, size=(HEIGHT, WIDTH), counts=rle_for(box))


def identity() -> GeometryTransform:
    """No scaling, no padding — the composite comes back exactly as it went in."""
    return GeometryTransform(
        scale=1.0,
        pad_x=0.0,
        pad_y=0.0,
        out_w=WIDTH,
        out_h=HEIGHT,
        source_size=(WIDTH, HEIGHT),
    )


def sample(**over: object) -> TrainingSample:
    base = {"path": "/pics/a.png", "width": WIDTH, "height": HEIGHT, "segmented": True}
    return TrainingSample(**{**base, **over})  # type: ignore[arg-type]


class TestTheVocabulary:
    def test_segmentation_gets_a_background_class_at_index_zero(self) -> None:
        """Every pixel belongs to some class and most belong to none of the annotated
        ones. Without background the loss can only ignore them, and a model that never
        sees background learns to label the whole frame."""
        classes = classes_for_task(
            SampleSet(mask_class_names=("signal", "mast")), "segmentation"
        )

        assert classes == (BACKGROUND_CLASS, "signal", "mast")

    def test_nothing_else_gets_one(self) -> None:
        # A detection cell with no box is simply not a positive; it needs no class.
        classes = classes_for_task(SampleSet(class_names=("signal",)), "detection")

        assert classes == ("signal",)

    def test_background_first_is_what_makes_the_viewer_draw_it_transparent(self) -> None:
        # The overlay registry treats class_names[0] === 'background' as the signal to
        # draw class 0 transparent, so a head trained here renders correctly with nothing
        # told about it. Index 0 is not merely a convention here.
        classes = classes_for_task(SampleSet(mask_class_names=("sky",)), "segmentation")

        assert classes[0] == BACKGROUND_CLASS

    def test_a_segmenter_never_sees_a_box_only_class(self) -> None:
        """The dead-channel bug. A COCO import with thirteen box classes plus one
        segmented class was giving the head fourteen outputs, twelve of which nothing
        could ever supervise — harmless to the model, and wrong in the class list, the
        metrics and the head's name."""
        mixed = SampleSet(
            class_names=("bishop", "king", "pawn"), mask_class_names=("train tracks",)
        )

        assert classes_for_task(mixed, "segmentation") == (BACKGROUND_CLASS, "train tracks")

    def test_a_detector_never_sees_a_mask_only_class(self) -> None:
        # The mirror, and it matters as much: a detector cannot learn a class that only
        # ever appeared as a mask.
        mixed = SampleSet(class_names=("bishop",), mask_class_names=("train tracks",))

        assert classes_for_task(mixed, "detection") == ("bishop",)


class TestTheGuard:
    def test_background_alone_does_not_count_as_a_learnable_class(self) -> None:
        """`classes_for_task` would report one class for a dataset with no masks at all,
        and the run would proceed to train a segmenter on nothing."""
        empty = SampleSet(class_names=("bishop",), mask_class_names=())

        assert classes_for_task(empty, "segmentation") == (BACKGROUND_CLASS,)
        assert learnable_classes(empty, "segmentation") == ()

    def test_a_mask_only_dataset_is_learnable_for_segmentation(self) -> None:
        only_masks = SampleSet(class_names=(), mask_class_names=("sky",))

        assert learnable_classes(only_masks, "segmentation") == ("sky",)
        assert learnable_classes(only_masks, "detection") == ()


class TestTheLabelMap:
    def test_a_positive_mask_paints_its_class_shifted_past_background(self) -> None:
        # `MaskTarget.class_index` is into the box vocabulary, which has no background
        # entry — so class 0 there is class 1 here.
        target = segmentation_target(sample(masks=(mask_target(0, (2, 2, 4, 4)),)), identity())

        assert int(target[0, 3, 3]) == 1
        assert int(target[0, 0, 0]) == 0

    def test_unannotated_pixels_are_background_not_ignored(self) -> None:
        """The difference between "nothing is here" and "nobody said". Inside the frame,
        a reviewer who segmented the image has said the rest is background."""
        target = segmentation_target(sample(masks=(mask_target(0, (0, 0, 2, 2)),)), identity())

        assert int(target[0, 10, 20]) == 0

    def test_a_later_mask_wins_an_overlap(self) -> None:
        # Last-writer-wins, the same rule the concept segmenter's own composite follows.
        target = segmentation_target(
            sample(masks=(mask_target(0, (0, 0, 10, 10)), mask_target(1, (0, 0, 10, 10)))),
            identity(),
        )

        assert int(target[0, 5, 5]) == 2

    def test_an_unclear_region_survives_a_positive_claiming_it(self) -> None:
        """`unclear` paints last, over everything. The reviewer's doubt is about that
        region, and resolving it in the model's favour is the one thing they did not say."""
        target = segmentation_target(
            sample(
                masks=(mask_target(0, (0, 0, 20, 20)),),
                ignore_masks=(mask_target(0, (0, 0, 5, 5)),),
            ),
            identity(),
        )

        assert int(target[0, 2, 2]) == IGNORE_INDEX
        assert int(target[0, 10, 10]) == 1

    def test_an_all_rejected_image_is_entirely_background(self) -> None:
        # Real supervision, and the reason a rejected mask is stored rather than deleted.
        target = segmentation_target(sample(masks=()), identity())

        assert set(torch.unique(target).tolist()) == {0}

    def test_it_carries_the_batch_dimension_every_other_target_carries(self) -> None:
        """A real run found this and these tests did not, because the first version of
        this file added the batch dimension itself before calling the loss. `run_epoch`
        does not: it passes `build_targets` straight through, and `cross_entropy` then read
        the height as the batch size — "Expected input batch_size (1) to match target
        batch_size (448)"."""
        target = segmentation_target(sample(masks=(mask_target(0, (1, 1, 3, 3)),)), identity())

        assert target.dtype == torch.long
        assert target.shape == (1, HEIGHT, WIDTH)


class TestThroughTheRealGeometry:
    def test_the_mask_lands_where_the_image_landed(self) -> None:
        """The failure this cannot be allowed to have: a mask offset by the letterbox
        supervises the wrong pixels, and the loss would report a plausible number the
        whole way."""
        plan = plan_preprocessing(_capabilities(), spec_for("linear-segmenter"))
        source = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
        _, transform = apply_geometry(plan, source)

        target = segmentation_target(
            sample(masks=(mask_target(0, (0, 0, WIDTH, HEIGHT)),)), transform
        )

        # The whole source is one class, so exactly the letterbox should be ignored.
        annotated = (target[0] != IGNORE_INDEX).numpy()
        moved, _ = apply_geometry(plan, source)
        content = np.asarray(moved).sum(axis=2) > 0
        assert np.array_equal(annotated, content)

    def test_padding_is_ignored_rather_than_background(self) -> None:
        # Padding is not background — it is not part of the picture at all, and training
        # on it teaches the model that the letterbox is a thing to predict.
        plan = plan_preprocessing(_capabilities(), spec_for("linear-segmenter"))
        _, transform = apply_geometry(plan, Image.new("RGB", (WIDTH, HEIGHT)))

        target = segmentation_target(sample(masks=(mask_target(0, (0, 0, 4, 4)),)), transform)

        assert IGNORE_INDEX in set(torch.unique(target).tolist())


class TestBuildTargets:
    def test_a_segmentation_head_gets_a_mask_and_no_boxes(self) -> None:
        """The `KeyError: 'mask'` this whole path exists to remove."""
        targets = build_targets(
            spec_for("linear-segmenter"),
            sample(masks=(mask_target(0, (1, 1, 4, 4)),)),
            identity(),
            grid=(4, 4),
            patch_size=10,
            num_classes=2,
        )

        assert "mask" in targets
        assert "boxes" not in targets

    def test_the_loss_accepts_what_build_targets_produces(self) -> None:
        """End to end, because the two halves were written years apart and never met."""
        targets = build_targets(
            spec_for("linear-segmenter"),
            sample(masks=(mask_target(0, (1, 1, 4, 4)),)),
            identity(),
            grid=(4, 4),
            patch_size=10,
            num_classes=2,
        )
        logits = torch.zeros(1, 2, HEIGHT, WIDTH, requires_grad=True)

        # **Untouched**, exactly as `run_epoch` passes it. Reshaping here is what let the
        # missing batch dimension through the first time.
        loss = segmentation_loss({"logits": logits}, targets)

        assert loss.requires_grad
        assert torch.isfinite(loss)

    def test_a_detection_head_is_untouched(self) -> None:
        targets = build_targets(
            spec_for("dense-detector"),
            sample(targets=((0, 1.0, 1.0, 4.0, 4.0),)),
            identity(),
            grid=(4, 4),
            patch_size=10,
            num_classes=1,
        )

        assert "boxes" in targets
        assert "mask" not in targets



@pytest.fixture(autouse=True)
def _quiet_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("ERROR")
