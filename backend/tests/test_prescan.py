"""Finding the images worth annotating (doc 53).

The rules that matter are the ones that quietly hide work from the user: a label match that
is too strict returns zero hits and reads as "the model found nothing", and an unreadable
file that stops the scan loses every image after it.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from PIL import Image

from app.datasets.models import Box
from app.ml.annotators.prescan import PrescanConfig, PrescanHit, matches, scan_boxes
from app.ml.annotators.prescan_runner import PrescanRunner


def box(prompt: str = "person", score: float | None = 0.9) -> Box:
    return Box(
        label="positive",
        provenance="grounding-dino",
        x=1.0,
        y=1.0,
        w=10.0,
        h=10.0,
        score=score,
        prompt=prompt,
    )


def config(**over: object) -> PrescanConfig:
    base: dict[str, object] = {
        "kind": "prompt",
        "image_paths": ("/a.jpg",),
        "model_id": "grounding-dino-tiny",
        "prompt": "a person",
    }
    return PrescanConfig(**{**base, **over})  # type: ignore[arg-type]


class TestTheConfig:
    def test_it_needs_images(self) -> None:
        with pytest.raises(ValueError, match="Nothing to scan"):
            config(image_paths=())

    def test_a_head_scan_needs_a_head(self) -> None:
        with pytest.raises(ValueError, match="instance_id"):
            PrescanConfig(kind="head", image_paths=("/a.jpg",), backbone_id="dinov2-small")

    def test_a_foundation_scan_needs_a_model(self) -> None:
        with pytest.raises(ValueError, match="foundation_id"):
            PrescanConfig(kind="foundation", image_paths=("/a.jpg",))

    def test_a_prompt_scan_needs_a_prompt(self) -> None:
        with pytest.raises(ValueError, match="prompt"):
            config(prompt="   ")

    def test_it_is_immutable(self) -> None:
        import dataclasses

        with pytest.raises(dataclasses.FrozenInstanceError):
            config().score_threshold = 0.9  # type: ignore[misc]


class TestLabelMatching:
    """The class a proposer reports is not always the phrase the user typed. Grounding DINO
    re-segments its prompt; a fine-tuned detector's names come from its dataset. Exact
    matching would return zero hits and read as "the model found nothing"."""

    def test_an_exact_name_matches(self) -> None:
        assert matches(box("person"), ("person",))

    def test_case_does_not_matter(self) -> None:
        assert matches(box("Person"), ("PERSON",))

    def test_a_resegmented_phrase_still_matches(self) -> None:
        # Ask for "chess piece", Grounding DINO answers "chess".
        assert matches(box("chess"), ("chess piece",))

    def test_a_longer_class_name_still_matches(self) -> None:
        assert matches(box("signal_pole"), ("signal",))

    def test_an_unrelated_class_does_not(self) -> None:
        assert not matches(box("bicycle"), ("person",))

    def test_no_labels_means_anything_counts(self) -> None:
        # Right default for a single-class head: asking the user to retype the only class
        # it knows is a question with one answer.
        assert matches(box("anything at all"), ())

    def test_a_box_with_no_class_never_matches_a_named_label(self) -> None:
        assert not matches(box(""), ("person",))

    def test_blank_labels_are_ignored_rather_than_matching_everything(self) -> None:
        # A trailing comma in the UI must not silently turn the filter off.
        assert not matches(box("bicycle"), ("person", "  "))


class TestScoring:
    def test_a_box_below_the_threshold_does_not_count(self) -> None:
        assert scan_boxes([box(score=0.1)], config(score_threshold=0.5)) is None

    def test_a_box_at_the_threshold_counts(self) -> None:
        assert scan_boxes([box(score=0.5)], config(score_threshold=0.5)) is not None

    def test_a_box_with_no_score_counts(self) -> None:
        # Hand-drawn and imported boxes carry none; treating that as 0 would hide them.
        assert scan_boxes([box(score=None)], config(score_threshold=0.9)) is not None

    def test_an_image_with_no_boxes_is_not_a_hit(self) -> None:
        assert scan_boxes([], config()) is None

    def test_the_hit_reports_what_was_found(self) -> None:
        hit = scan_boxes([box("person", 0.4), box("dog", 0.8)], config())
        assert hit is not None
        assert hit.boxes == 2
        assert hit.best_score == pytest.approx(0.8)
        assert hit.labels == ("dog", "person")

    def test_only_matching_boxes_are_counted(self) -> None:
        # The count is what the user sees beside the image; counting rejects would promise
        # boxes that the session will not show.
        hit = scan_boxes([box("person"), box("bicycle")], config(labels=("person",)))
        assert hit is not None and hit.boxes == 1


class TestTheRunner:
    def _images(self, directory: Path, count: int) -> tuple[str, ...]:
        paths = []
        for index in range(count):
            path = directory / f"{index}.png"
            Image.new("RGB", (20, 20)).save(path)
            paths.append(str(path))
        return tuple(paths)

    def _wait(self, runner: PrescanRunner, job_id: str) -> None:
        for _ in range(200):
            job = runner.get(job_id)
            if job is not None and job.finished:
                return
            threading.Event().wait(0.02)
        raise AssertionError("prescan did not finish")

    def test_it_keeps_only_the_images_with_a_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        paths = self._images(tmp_path, 4)
        hits = {paths[1], paths[3]}
        current = [""]

        def reader(path: str) -> tuple[Image.Image, Path]:
            current[0] = path
            return Image.new("RGB", (20, 20)), Path(path)

        monkeypatch.setattr("app.ml.annotators.prescan_runner.read_image", reader)
        monkeypatch.setattr(
            "app.ml.annotators.prescan_runner.propose_for",
            lambda image, cfg, settings=None: [box()] if current[0] in hits else [],
        )

        runner = PrescanRunner()
        job = runner.submit(config(image_paths=paths))
        self._wait(runner, job.job_id)
        assert {hit.path for hit in job.hits} == hits
        assert job.scanned == 4

    def test_an_unreadable_image_is_counted_not_fatal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # One truncated PNG in four hundred frames must not lose the other 399.
        paths = self._images(tmp_path, 3)
        Path(paths[1]).write_bytes(b"not a png")
        monkeypatch.setattr(
            "app.ml.annotators.prescan_runner.propose_for",
            lambda image, cfg, settings=None: [box()],
        )
        runner = PrescanRunner()
        job = runner.submit(config(image_paths=paths))
        self._wait(runner, job.job_id)
        assert job.state == "complete"
        assert job.unreadable == 1
        assert len(job.hits) == 2
        assert job.scanned == 3

    def test_a_failing_model_fails_the_job_rather_than_reporting_nothing_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # "Nothing found" and "the model never ran" must not look the same.
        def explode(image: object, cfg: object, settings: object = None) -> list[Box]:
            raise RuntimeError("weights missing")

        monkeypatch.setattr("app.ml.annotators.prescan_runner.propose_for", explode)
        runner = PrescanRunner()
        job = runner.submit(config(image_paths=self._images(tmp_path, 2)))
        self._wait(runner, job.job_id)
        assert job.state == "failed"
        assert "weights missing" in job.message

    def test_cancelling_keeps_what_it_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        paths = self._images(tmp_path, 40)
        started = threading.Event()

        def slow(image: object, cfg: object, settings: object = None) -> list[Box]:
            started.set()
            threading.Event().wait(0.02)
            return [box()]

        monkeypatch.setattr("app.ml.annotators.prescan_runner.propose_for", slow)
        runner = PrescanRunner()
        job = runner.submit(config(image_paths=paths))
        started.wait(2.0)
        runner.cancel(job.job_id)
        self._wait(runner, job.job_id)
        assert job.state == "cancelled"
        assert job.hits, "a cancelled scan must keep the answer it had reached"
        assert job.scanned < job.total

    def test_the_snapshot_agrees_with_itself(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Read one field at a time they can disagree — 8 scanned, 9 hits — which reads as a
        # counting bug rather than as a race.
        monkeypatch.setattr(
            "app.ml.annotators.prescan_runner.propose_for",
            lambda image, cfg, settings=None: [box()],
        )
        runner = PrescanRunner()
        job = runner.submit(config(image_paths=self._images(tmp_path, 5)))
        self._wait(runner, job.job_id)
        scanned, unreadable, hits = job.snapshot()
        assert scanned == 5 and unreadable == 0 and len(hits) == 5

    def test_an_unknown_job_is_none(self) -> None:
        assert PrescanRunner().get("nope") is None

    def test_cancelling_an_unknown_job_is_false(self) -> None:
        assert PrescanRunner().cancel("nope") is False


class TestHitShape:
    def test_a_hit_is_immutable(self) -> None:
        import dataclasses

        hit = PrescanHit(path="/a.jpg", boxes=1, best_score=0.5, labels=("person",))
        with pytest.raises(dataclasses.FrozenInstanceError):
            hit.boxes = 2  # type: ignore[misc]
