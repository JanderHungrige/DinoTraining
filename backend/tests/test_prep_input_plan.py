"""The model-input plan over hand-built facts (doc 85)."""

from __future__ import annotations

from app.prep.input_plan import grid_for, plan_input
from app.prep.profiles import get_profile
from app.prep.stats import AnnotationFacts, DatasetFacts, ImageFacts


def facts(side: float, width: int = 2464, height: int = 1600, kind: str = "box") -> DatasetFacts:
    return DatasetFacts(
        dataset_id="d",
        images=[ImageFacts(i, f"/img/{i}.jpg", width, height, None) for i in range(40)],
        annotations=[
            AnnotationFacts(i, kind, "positive", "signal", "signal", side, side, 100, 100)
            for i in range(40)
        ],
    )


def test_large_objects_need_no_tiles() -> None:
    plan = plan_input(facts(400), get_profile("rf-detr-nano"))
    assert plan.fit == "stretch" and "squeezed" in plan.fit_explained
    assert plan.tiling.recommended is False
    assert plan.objects is not None and plan.objects.too_small_share == 0
    assert "large enough" in plan.tiling.reason


def test_small_objects_get_the_smallest_grid_that_makes_them_visible() -> None:
    # 60 px in a 2464 px frame is 9.4 px at RF-DETR's 384 px input: below its 16 px.
    plan = plan_input(facts(60), get_profile("rf-detr-nano"))
    assert plan.objects is not None and plan.objects.p10_px < 16
    tiling = plan.tiling
    assert tiling.recommended and tiling.objects_after is not None
    assert tiling.objects_after.p10_px >= 16
    # Wide frame: more columns than rows, and not more tiles than needed.
    assert tiling.columns > tiling.rows
    smaller = plan_input(facts(60), get_profile("rf-detr-nano"), grid=tiling.columns - 1)
    assert smaller.tiling.objects_after is not None
    assert smaller.tiling.objects_after.p10_px < 16


def test_turning_tiling_off_says_what_it_costs() -> None:
    plan = plan_input(facts(60), get_profile("rf-detr-nano"), grid=1)
    assert plan.tiling.recommended is False
    assert "100% of objects stay below" in plan.tiling.reason


def test_outlines_are_not_tiled_and_the_user_is_told_why() -> None:
    plan = plan_input(facts(20, kind="mask"), get_profile("sam2.1-hiera-small"))
    assert plan.tiling.supported is False and plan.tiling.recommended is False
    assert "crop" in plan.tiling.reason
    assert plan.masks is not None and "ignore" in plan.masks


def test_classification_crops_the_centre_and_says_so() -> None:
    plan = plan_input(facts(400), get_profile("head-classification-dinov2"))
    assert plan.fit == "center-crop"
    assert "cut off" in plan.fit_explained
    assert plan.objects is None


def test_letterbox_padding_is_reported_for_the_typical_image() -> None:
    wide = facts(400, width=2000, height=1000)
    plan = plan_input(wide, get_profile("head-detection-dinov2"))
    assert plan.typical_source == (2000, 1000)
    assert plan.padding_share == 0.5
    # A stretch fills the square: no padding at all.
    assert plan_input(wide, get_profile("rf-detr-nano")).padding_share == 0


def test_grids_follow_the_frame_shape() -> None:
    assert grid_for(2464, 1600, 4) == (4, 3)
    assert grid_for(1600, 2464, 4) == (3, 4)
    assert grid_for(100, 100, 1) == (1, 1)


def test_every_class_gets_its_own_colour() -> None:
    from app.prep.input_preview import colours_for

    many = DatasetFacts(
        dataset_id="d",
        images=[ImageFacts(0, "/a.jpg", 100, 100, None)],
        annotations=[
            AnnotationFacts(0, "box", "positive", f"c{i:02d}", "", 5, 5, 0, 0) for i in range(13)
        ],
    )
    colours = colours_for(many)
    assert len(set(colours.values())) == 13
