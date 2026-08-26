"""Grounding DINO behind the foundation contract (doc 66).

Reported as "Grounding DINO is not available in the Inference Viewer or the Dataset
Generator?" — correct, because the catalogue had no way to describe it. It is prompted like
a mask annotator and returns boxes like a detector, and `takes_concept` was defined as
`annotator_id is not None`, which fused those two independent axes.

The detector itself is stubbed: `detector.py` owns prompting and the xyxy→xywh conversion
and has its own tests, so what is worth pinning here is the *joining* — that the prompt
reaches the model, that phrases become class indices, and that an empty prompt loads
nothing.
"""

from __future__ import annotations

import pytest
from PIL import Image

from app.ml.detector import Detection
from app.ml.foundation.build import build_foundation
from app.ml.foundation.prompt_detect import PromptedDetector, _box_payload
from app.ml.foundation.registry import get_foundation


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Patch the detector stage and record what it was asked for."""
    calls: dict[str, object] = {"loaded": None, "prompt": None, "threshold": None}

    def fake_load(model_id: str = "") -> object:
        calls["loaded"] = model_id
        return object()

    def fake_detect(
        detector: object,
        image: Image.Image,
        prompt: str,
        box_threshold: float = 0.3,
        **_: object,
    ) -> list[Detection]:
        calls["prompt"] = prompt
        calls["threshold"] = box_threshold
        return list(calls.get("detections") or [])

    monkeypatch.setattr("app.ml.foundation.prompt_detect.load_detector", fake_load)
    monkeypatch.setattr("app.ml.foundation.prompt_detect.detect", fake_detect)
    return calls


def box(text: str, x: float = 1.0, score: float = 0.9) -> Detection:
    return Detection(x=x, y=2.0, w=10.0, h=20.0, score=score, text=text)


def image() -> Image.Image:
    return Image.new("RGB", (40, 30))


class TestTheCatalogueCanDescribeIt:
    def test_it_is_prompted_and_returns_boxes(self) -> None:
        """The combination the old derived `takes_concept` could not express: every
        prompted model used to be a mask pipeline, so "prompted" was read off "pipeline"."""
        spec = get_foundation("grounding-dino-tiny")
        assert spec is not None
        assert spec.takes_concept is True
        assert spec.render_hint == "boxes"
        assert spec.annotator_id is None

    def test_rf_detr_stays_unprompted(self) -> None:
        # The other side of the same axis — decoupling must not make everything prompted.
        spec = get_foundation("rf-detr-nano")
        assert spec is not None
        assert spec.takes_concept is False

    def test_both_sizes_are_offered(self) -> None:
        for spec_id in ("grounding-dino-tiny", "grounding-dino-base"):
            spec = get_foundation(spec_id)
            assert spec is not None and spec.prompted

    def test_each_size_names_its_own_weights(self) -> None:
        """A variant that quietly runs the default weights looks entirely correct — same
        boxes, same timings — and the download it was chosen for is never touched."""
        tiny = get_foundation("grounding-dino-tiny")
        base = get_foundation("grounding-dino-base")
        assert tiny is not None and base is not None
        assert tiny.model_id == "grounding-dino-tiny"
        assert base.model_id == "grounding-dino-base"

    def test_the_builder_returns_a_prompted_detector(self) -> None:
        """Dispatch order matters: a prompted detector reports `task == "detection"` too,
        so a fall-through would hand it to RF-DETR's loader."""
        assert isinstance(build_foundation("grounding-dino-tiny"), PromptedDetector)


class TestThePromptReachesTheModel:
    def test_it_passes_the_concept_through(self, stub: dict[str, object]) -> None:
        spec = get_foundation("grounding-dino-tiny")
        assert spec is not None
        PromptedDetector(spec).predict(image(), "a bolt. a nut.", 0.4)

        assert stub["prompt"] == "a bolt. a nut."
        assert stub["threshold"] == 0.4

    def test_it_loads_the_weights_its_own_row_names(self, stub: dict[str, object]) -> None:
        spec = get_foundation("grounding-dino-base")
        assert spec is not None
        PromptedDetector(spec).predict(image(), "a bolt")

        assert stub["loaded"] == "grounding-dino-base"


class TestAnEmptyPromptIsNotAnError:
    def test_it_returns_an_empty_prediction(self, stub: dict[str, object]) -> None:
        """The state before the user has typed. Running Grounding DINO on "" matches
        everything weakly and returns noise that reads as a detector having a bad day."""
        spec = get_foundation("grounding-dino-tiny")
        assert spec is not None
        prediction = PromptedDetector(spec).predict(image(), "")

        assert prediction.payload["boxes"] == []
        assert prediction.class_names == ()

    def test_it_loads_nothing(self, stub: dict[str, object]) -> None:
        # Not just cosmetic: this is what stops an empty field costing a model load, and
        # what lets the viewer offer the model before anything is installed-and-warm.
        spec = get_foundation("grounding-dino-tiny")
        assert spec is not None
        PromptedDetector(spec).predict(image(), "   ")

        assert stub["loaded"] is None

    def test_a_whitespace_prompt_counts_as_empty(self, stub: dict[str, object]) -> None:
        spec = get_foundation("grounding-dino-tiny")
        assert spec is not None
        PromptedDetector(spec).predict(image(), "\n\t ")

        assert stub["prompt"] is None


class TestPhrasesBecomeClasses:
    def test_each_distinct_phrase_gets_one_index(self) -> None:
        """Grounding DINO answers with a phrase per box, not a class index. The renderer
        colours by index, so a phrase mapping to two indices is two colours for one thing."""
        payload, names = _box_payload([box("bolt"), box("nut"), box("bolt")])

        assert names == ("bolt", "nut")
        assert payload["classes"] == [0, 1, 0]

    def test_indices_start_at_zero(self) -> None:
        """Unlike the mask payload, which reserves 0 for background. A box payload has no
        background — every box is something — and an off-by-one here would name every box
        after the previous phrase."""
        _, names = _box_payload([box("sky")])
        payload, _ = _box_payload([box("sky")])

        assert names == ("sky",)
        assert payload["classes"] == [0]

    def test_phrases_keep_first_appearance_order(self) -> None:
        _, names = _box_payload([box("nut"), box("bolt")])

        assert names == ("nut", "bolt")

    def test_boxes_scores_and_classes_stay_aligned(self) -> None:
        """Read positionally downstream. A partial drop misattributes every later box —
        a silent mislabel rather than a crash."""
        payload, _ = _box_payload([box("bolt", score=0.9), box("nut", score=0.5)])

        assert payload["scores"] == [0.9, 0.5]
        assert len(payload["boxes"]) == len(payload["classes"]) == 2

    def test_a_zero_area_box_is_dropped_from_all_three(self) -> None:
        degenerate = Detection(x=1.0, y=1.0, w=0.0, h=5.0, score=0.9, text="ghost")
        payload, _ = _box_payload([box("bolt"), degenerate])

        assert len(payload["boxes"]) == 1
        assert payload["classes"] == [0]

    def test_no_detections_gives_empty_everything(self) -> None:
        payload, names = _box_payload([])

        assert payload["boxes"] == [] and payload["classes"] == []
        assert names == ()


class TestThePrediction:
    def test_it_reports_boxes_so_the_studio_can_review_them(
        self, stub: dict[str, object]
    ) -> None:
        stub["detections"] = [box("bolt")]
        spec = get_foundation("grounding-dino-tiny")
        assert spec is not None
        prediction = PromptedDetector(spec).predict(image(), "a bolt")

        assert prediction.render_hint == "boxes"
        assert prediction.task == "detection"
        assert prediction.class_names == ("bolt",)

    def test_it_identifies_itself_by_its_catalogue_id(self, stub: dict[str, object]) -> None:
        # The viewer keys results by `instance_id`; two sizes reporting the same id would
        # overwrite each other in a comparison run.
        stub["detections"] = [box("bolt")]
        spec = get_foundation("grounding-dino-base")
        assert spec is not None
        prediction = PromptedDetector(spec).predict(image(), "a bolt")

        assert prediction.instance_id == "grounding-dino-base"
