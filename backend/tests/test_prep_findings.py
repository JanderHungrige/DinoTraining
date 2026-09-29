"""The audit's rules, over hand-built facts (doc 81)."""

from __future__ import annotations

from app.prep.finding_types import AuditContext
from app.prep.findings import evaluate
from app.prep.profiles import get_profile
from app.prep.stats import AnnotationFacts, DatasetFacts, ImageFacts


def facts(images: int, boxes: list[tuple[int, str, float]], size: int = 2464) -> DatasetFacts:
    """`boxes` are (image id, class, side in px)."""
    return DatasetFacts(
        dataset_id="d",
        images=[ImageFacts(i, f"/img/{i}.jpg", size, size * 2 // 3, None) for i in range(images)],
        annotations=[
            AnnotationFacts(i, "box", "positive", cls, cls, side, side, 0, 0)
            for i, cls, side in boxes
        ],
    )


def ids(ctx: AuditContext) -> dict[str, str]:
    return {f.id: f.severity for f in evaluate(ctx)}


def test_a_healthy_dataset_has_no_problems() -> None:
    boxes = [(i, "car" if i % 2 else "bus", 400) for i in range(200)]
    found = ids(AuditContext(facts(200, boxes), get_profile("rf-detr-nano")))
    assert "problem" not in found.values()


def test_objects_that_vanish_at_the_model_input_are_a_problem_with_a_grid() -> None:
    # Doc 49's case: ~11 px signals in 2464 px frames, which is 1.7 px at 384 px.
    boxes = [(i, "signal", 11) for i in range(150)]
    ctx = AuditContext(facts(150, boxes), get_profile("rf-detr-nano"))
    finding = next(f for f in evaluate(ctx) if f.id == "objects-too-small")
    assert finding.severity == "problem"
    assert finding.metrics["median_px"] < 2
    assert finding.metrics["suggested_grid"] >= 2


def test_a_class_with_a_single_example_is_flagged_and_named() -> None:
    boxes = [(i, "pawn", 200) for i in range(120)] + [(0, "bishop", 200)]
    found = {f.id: f for f in evaluate(AuditContext(facts(120, boxes), None))}
    assert found["thin-classes"].severity == "problem"
    assert "bishop (1)" in found["thin-classes"].what
    assert found["class-imbalance"].severity == "problem"


def test_spellings_of_one_class_are_spotted() -> None:
    boxes = [(i, "traffic-light" if i % 2 else "traffic lights", 200) for i in range(120)]
    assert "class-spellings" in ids(AuditContext(facts(120, boxes), None))


def test_a_segmentation_target_without_masks_is_a_problem() -> None:
    boxes = [(i, "car", 200) for i in range(120)]
    ctx = AuditContext(facts(120, boxes), get_profile("head-segmentation-dinov2"))
    assert ids(ctx)["wrong-annotation-kind"] == "problem"


def test_without_a_target_size_rules_are_skipped() -> None:
    boxes = [(i, "signal", 11) for i in range(150)]
    assert "objects-too-small" not in ids(AuditContext(facts(150, boxes), None))


def test_problems_come_first() -> None:
    boxes = [(i, "pawn", 200) for i in range(15)] + [(0, "bishop", 200)]
    severities = [f.severity for f in evaluate(AuditContext(facts(15, boxes), None))]
    assert severities == sorted(severities, key={"problem": 0, "warn": 1, "info": 2}.get)
