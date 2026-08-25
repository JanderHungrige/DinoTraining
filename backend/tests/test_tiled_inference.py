"""Running a head over the grid it was trained on (doc 62).

The gap this closes is the worst kind: a head trained on 616 px tiles found nothing on a
full 2464 px frame, and the run *succeeded* — right pass count, right elapsed time, empty
list. Nothing distinguished it from an image with nothing in it.

The merge is where the logic is, so that is what is tested here rather than the forward
pass: a tile's boxes are in tile coordinates and have to become frame coordinates, the
overlap that keeps a seam object whole also finds it twice, and a 1x1 grid must not take a
different route from no grid at all.
"""

from __future__ import annotations

import pytest

from app.datasets.tiling import Tile, plan_tiles
from app.ml.heads.registry import get_head_type
from app.ml.inference.engine import ResolvedHead
from app.ml.inference.results import Prediction
from app.ml.inference.tiled import TileGrid, merge_tiles


def spec_for(head_id: str):
    found = get_head_type(head_id)
    assert found is not None
    return found


def head(head_id: str = "dense-detector") -> ResolvedHead:
    """A ResolvedHead with only what `merge_tiles` reads: the spec's render hint."""
    return ResolvedHead(instance=None, spec=spec_for(head_id))  # type: ignore[arg-type]


def prediction(
    boxes: list[tuple[float, float, float, float]],
    scores: list[float] | None = None,
    classes: list[int] | None = None,
    render_hint: str = "boxes",
    elapsed_ms: float = 10.0,
) -> Prediction:
    return Prediction(
        instance_id="h1",
        head_name="Rail detector",
        head_type_id="dense-detector",
        task="detection",
        render_hint=render_hint,  # type: ignore[arg-type]
        class_names=("signal", "mast"),
        payload={
            "boxes": [list(box) for box in boxes],
            "scores": scores if scores is not None else [0.9] * len(boxes),
            "classes": classes if classes is not None else [0] * len(boxes),
        },
        grid=(32, 32),
        elapsed_ms=elapsed_ms,
    )


def tile(x: int, y: int, column: int = 0, row: int = 0) -> Tile:
    return Tile(x=x, y=y, width=100, height=100, column=column, row=row)


def boxes_of(result: Prediction) -> list[list[float]]:
    payload = result.payload["boxes"]
    assert isinstance(payload, list)
    return payload


class TestTheGrid:
    def test_a_one_by_one_grid_is_the_whole_frame(self) -> None:
        """And is not an error. It takes the untiled path in `run_heads`, so a tiled and
        an untiled answer cannot drift apart for reasons nobody can see."""
        assert TileGrid(columns=1, rows=1).is_whole_frame is True
        assert TileGrid(columns=2, rows=1).is_whole_frame is False

    def test_it_uses_the_planner_doc_49_tiles_with(self) -> None:
        # Not a second implementation: an inference grid differing from the training grid
        # by a rounding rule puts every box slightly off, and nothing raises.
        tiles = plan_tiles(2464, 1600, 4, 3)

        assert len(tiles) == 12
        # The last tile ends exactly at the frame edge — the planner's own guarantee.
        assert tiles[-1].x + tiles[-1].width == 2464
        assert tiles[-1].y + tiles[-1].height == 1600


class TestMergingCoordinates:
    def test_a_tiles_boxes_become_frame_boxes(self) -> None:
        """The one line that makes a tile's answer a frame's answer. Without it every box
        from every tile lands in the top-left corner."""
        merged = merge_tiles(
            [prediction([(10, 20, 5, 5)]), prediction([(10, 20, 5, 5)])],
            [tile(0, 0), tile(200, 300)],
            head(),
        )

        assert sorted(boxes_of(merged)) == [[10, 20, 5, 5], [210, 320, 5, 5]]

    def test_width_and_height_are_not_offset(self) -> None:
        # Only the origin moves. Offsetting the extent would grow every box by its tile's
        # position, which looks plausible at the top-left and absurd at the bottom-right.
        merged = merge_tiles(
            [prediction([(1, 2, 30, 40)])], [tile(500, 600)], head()
        )

        assert boxes_of(merged) == [[501, 602, 30, 40]]

    def test_an_empty_tile_contributes_nothing_and_does_not_break_the_rest(self) -> None:
        merged = merge_tiles(
            [prediction([]), prediction([(5, 5, 10, 10)])],
            [tile(0, 0), tile(100, 0)],
            head(),
        )

        assert boxes_of(merged) == [[105, 5, 10, 10]]

    def test_every_tile_being_empty_is_an_empty_result_not_a_crash(self) -> None:
        merged = merge_tiles(
            [prediction([]), prediction([])], [tile(0, 0), tile(100, 0)], head()
        )

        assert boxes_of(merged) == []


class TestSuppressingTheSeam:
    def test_the_same_object_found_in_two_tiles_survives_once(self) -> None:
        """Overlap exists so an object on a seam is whole in *some* tile. The cost is that
        it is found twice, and NMS is exactly what that costs."""
        merged = merge_tiles(
            [
                prediction([(90, 10, 20, 20)], scores=[0.7]),
                prediction([(0, 10, 20, 20)], scores=[0.9]),
            ],
            # Tiles overlapping by 10px, so both describe the same frame rectangle.
            [tile(0, 0), tile(90, 0)],
            head(),
        )

        assert len(boxes_of(merged)) == 1

    def test_the_higher_scoring_duplicate_is_the_one_kept(self) -> None:
        merged = merge_tiles(
            [
                prediction([(90, 10, 20, 20)], scores=[0.55]),
                prediction([(0, 10, 20, 20)], scores=[0.95]),
            ],
            [tile(0, 0), tile(90, 0)],
            head(),
        )

        scores = merged.payload["scores"]
        assert isinstance(scores, list)
        assert scores == [pytest.approx(0.95)]

    def test_suppression_is_class_aware(self) -> None:
        """A rail beside a signal legitimately overlaps, and suppressing across classes
        would delete the rarer one — doc 43's rule, applied across tiles too."""
        merged = merge_tiles(
            [
                prediction([(90, 10, 20, 20)], scores=[0.7], classes=[0]),
                prediction([(0, 10, 20, 20)], scores=[0.9], classes=[1]),
            ],
            [tile(0, 0), tile(90, 0)],
            head(),
        )

        assert len(boxes_of(merged)) == 2

    def test_two_genuinely_separate_objects_both_survive(self) -> None:
        merged = merge_tiles(
            [prediction([(5, 5, 10, 10)]), prediction([(5, 5, 10, 10)])],
            [tile(0, 0), tile(500, 500)],
            head(),
        )

        assert len(boxes_of(merged)) == 2


class TestWhatItLeavesAlone:
    def test_a_non_box_head_comes_back_untouched(self) -> None:
        """A tiled depth map would show its seams and a tiled label map is a different
        feature. The request is coherent; tiling simply has nothing to do."""
        first = prediction([], render_hint="depth-map")
        merged = merge_tiles([first, prediction([], render_hint="depth-map")],
                             [tile(0, 0), tile(100, 0)], head("linear-depth"))

        assert merged is first

    def test_provenance_survives_the_merge(self) -> None:
        # The name, the classes and the head type all come from the tiles, so a merged
        # prediction is indistinguishable from an untiled one to everything downstream.
        merged = merge_tiles([prediction([(1, 1, 2, 2)])], [tile(0, 0)], head())

        assert merged.head_name == "Rail detector"
        assert merged.class_names == ("signal", "mast")
        assert merged.render_hint == "boxes"


class TestWhatItReports:
    def test_elapsed_is_the_sum_of_the_tiles(self) -> None:
        """The sum, not the max. Every tile's decode was really paid for, and reporting
        one tile's time would make tiling look free — the opposite of the trade."""
        merged = merge_tiles(
            [prediction([], elapsed_ms=10.0), prediction([], elapsed_ms=15.0)],
            [tile(0, 0), tile(100, 0)],
            head(),
        )

        assert merged.elapsed_ms == pytest.approx(25.0)

    def test_a_mismatched_payload_is_dropped_rather_than_mispaired(self) -> None:
        """Boxes, scores and classes are aligned by construction. A payload where they are
        not came from something other than `boxes_payload`, and pairing box i with score j
        is a silent mislabel."""
        broken = prediction([(1, 1, 2, 2)])
        broken.payload["scores"] = [0.9, 0.8]

        merged = merge_tiles(
            [broken, prediction([(5, 5, 2, 2)])], [tile(0, 0), tile(100, 0)], head()
        )

        assert boxes_of(merged) == [[105, 5, 2, 2]]
