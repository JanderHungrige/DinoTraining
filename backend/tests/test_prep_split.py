"""A split that cannot leak: groups stay together, video frames get a buffer (doc 84)."""

from __future__ import annotations

from collections import Counter

from app.prep.split import BUFFER, assign, build_groups, mark_buffers
from app.prep.stats import AnnotationFacts, DatasetFacts, ImageFacts


def video(frames: int, cls: str = "signal") -> DatasetFacts:
    return DatasetFacts(
        dataset_id="d",
        images=[
            ImageFacts(i, f"/f/{i}.jpg", 100, 100, "/v/ride.mp4", i * 2) for i in range(frames)
        ],
        annotations=[
            AnnotationFacts(i, "box", "positive", cls, cls, 10, 10, 0, 0) for i in range(frames)
        ],
    )


def split_of(
    facts: DatasetFacts, scenes: list[list[str]] | None = None, seed: int = 1
) -> dict[int, str]:
    groups = build_groups(facts, scenes or [])
    fractions = {"train": 0.7, "val": 0.2, "test": 0.1}
    return mark_buffers(facts, assign(groups, fractions, seed))


def test_one_video_is_still_split_into_every_side() -> None:
    sides = Counter(split_of(video(300)).values())
    assert sides["train"] > 150
    assert sides["val"] > 30
    assert sides["test"] > 10


def test_no_evaluation_frame_has_a_training_frame_beside_it() -> None:
    # The whole point: a test frame's neighbour is a near-copy, so it must not be in training.
    sides = split_of(video(300))
    order = list(range(300))
    for a, b in zip(order, order[1:], strict=False):
        pair = {sides[a], sides[b]}
        assert not (pair & {"val", "test"} and "train" in pair), (a, b, sides[a], sides[b])
    assert Counter(sides.values())[BUFFER] > 0


def test_a_scene_group_never_straddles_two_sides() -> None:
    facts = DatasetFacts(
        dataset_id="d",
        images=[ImageFacts(i, f"/p/{i}.jpg", 100, 100, None) for i in range(40)],
        annotations=[
            AnnotationFacts(i, "box", "positive", "car", "car", 5, 5, 0, 0) for i in range(40)
        ],
    )
    scene = [f"/p/{i}.jpg" for i in range(10)]
    sides = split_of(facts, [scene])
    assert len({sides[i] for i in range(10)}) == 1


def test_a_rare_class_reaches_validation_when_it_can() -> None:
    images = [ImageFacts(i, f"/p/{i}.jpg", 100, 100, None) for i in range(100)]
    annotations = [
        AnnotationFacts(i, "box", "positive", "rare" if i % 10 == 0 else "common", "", 5, 5, 0, 0)
        for i in range(100)
    ]
    sides = split_of(DatasetFacts("d", images, annotations))
    rare_sides = Counter(sides[i] for i in range(0, 100, 10))
    assert rare_sides["val"] >= 1
    assert rare_sides["train"] >= 5


def test_the_same_seed_gives_the_same_split() -> None:
    assert split_of(video(120), seed=7) == split_of(video(120), seed=7)


def sparse_video() -> DatasetFacts:
    """Two annotated stretches of one video, far apart: frames 0-4 and 16-20, every 2nd."""
    indices = [0, 2, 4, 16, 18, 20]
    return DatasetFacts(
        dataset_id="d",
        images=[
            ImageFacts(i, f"/f/{i}.jpg", 100, 100, "/v/ride.mp4", f) for i, f in enumerate(indices)
        ],
        annotations=[
            AnnotationFacts(i, "box", "positive", "piece", "", 5, 5, 0, 0) for i in range(6)
        ],
    )


def test_a_gap_in_the_frames_is_a_natural_boundary_that_needs_no_buffer() -> None:
    # Found live: the stretches were treated as adjacent, buffers swallowed every
    # evaluation frame, and val and test came out empty.
    facts = sparse_video()
    groups = build_groups(facts, [])
    stretches = sorted(tuple(g.image_ids) for g in groups)
    assert stretches == [(0, 1, 2), (3, 4, 5)]
    sides = mark_buffers(facts, {0: "train", 1: "train", 2: "train", 3: "val", 4: "val", 5: "val"})
    assert list(sides.values()).count(BUFFER) == 0


def test_a_buffer_never_empties_an_evaluation_run() -> None:
    facts = DatasetFacts(
        dataset_id="d",
        images=[ImageFacts(i, f"/f/{i}.jpg", 100, 100, "/v/a.mp4", i) for i in range(9)],
    )
    sides = {i: "train" for i in range(9)} | {3: "val", 4: "val", 5: "val"}
    marked = mark_buffers(facts, sides)
    assert [i for i in range(9) if marked[i] == "val"] == [4]
    assert [i for i in range(9) if marked[i] == BUFFER] == [3, 5]
