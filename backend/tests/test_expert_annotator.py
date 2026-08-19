"""Tests for running a trained head as an auto-annotator.

Two things carry the feature. A detection becomes a *stored annotation shape* without any
coordinate conversion — doc 16 chose the store's xywh/top-left convention precisely so this
wave could consume it directly, and a conversion appearing here would be a regression. And
a head that cannot produce boxes is refused with a reason a user can act on, rather than
returning an empty list that looks like "found nothing".
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import torch
from fastapi.testclient import TestClient

from tests.inference_api_testkit import (
    add_classifier,
    add_detector,
    add_segmenter,
    stub_inference_client,
    write_image,
)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    yield from stub_inference_client(tmp_path, monkeypatch)


def propose(
    client: TestClient, image: str, instance_id: str, **overrides: object
) -> object:
    payload = {
        "image_path": image,
        "backbone_id": "dinov2-small",
        "instance_id": instance_id,
        **overrides,
    }
    return client.post("/api/v1/generate/expert", json=payload)


class TestProposal:
    def test_a_detection_head_returns_boxes(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        image = write_image(tmp_path / "a.png")
        response = propose(client, image, add_detector(), score_threshold=0.0)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["boxes"], list)

    def test_every_proposal_is_marked_as_coming_from_a_head(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        image = write_image(tmp_path / "a.png")
        body = propose(client, image, add_detector(), score_threshold=0.0).json()

        assert body["boxes"], "threshold 0 should keep something to assert on"
        assert all(box["provenance"] == "expert-head" for box in body["boxes"])

    def test_proposals_start_positive_for_the_reviewer_to_demote(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """`unclear` would claim the model expressed doubt; that verdict is the user's."""
        image = write_image(tmp_path / "a.png")
        body = propose(client, image, add_detector(), score_threshold=0.0).json()
        assert all(box["label"] == "positive" for box in body["boxes"])

    def test_boxes_carry_the_predicted_class_and_score(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        image = write_image(tmp_path / "a.png")
        body = propose(client, image, add_detector(), score_threshold=0.0).json()

        for box in body["boxes"]:
            assert box["prompt"].startswith("object")
            assert 0.0 <= box["score"] <= 1.0

    def test_boxes_are_inside_the_source_image(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """The dataset store rejects an out-of-frame box, so a bad convention 422s later.

        Asserting it here means the failure names the annotator rather than the store.
        """
        image = write_image(tmp_path / "a.png", size=(320, 240))
        body = propose(client, image, add_detector(), score_threshold=0.0).json()

        assert (body["width"], body["height"]) == (320, 240)
        for box in body["boxes"]:
            assert box["x"] >= 0 and box["y"] >= 0
            assert box["x"] + box["w"] <= 320
            assert box["y"] + box["h"] <= 240
            assert box["w"] > 0 and box["h"] > 0

    def test_the_response_identifies_the_head_by_provenance_not_filename(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        image = write_image(tmp_path / "a.png")
        body = propose(client, image, add_detector(name="Bolt finder")).json()

        # The pair Wave 3's picker shows: the user's label, and what the head does.
        assert body["head_name"] == "Bolt finder"
        assert "detection" in body["head_summary"].lower()
        for field in (body["head_name"], body["head_summary"]):
            assert ".safetensors" not in field
            assert ".pt" not in field

    def test_every_returned_box_satisfies_the_requested_threshold(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """The direct contract, rather than comparing two counts.

        A count comparison looked obvious and was wrong twice over: the stub draws fresh
        random features per request, so two calls are not comparable, and its random conv
        weights saturate sigmoid — nearly every score lands above 0.99, so even a 0.99
        threshold filters nothing and `few < many` fails on identical data. What is always
        true, saturated or not, is that nothing below the threshold comes back.
        """
        image = write_image(tmp_path / "a.png")
        instance = add_detector()

        for threshold in (0.0, 0.5, 0.9, 1.0):
            boxes = propose(client, image, instance, score_threshold=threshold).json()[
                "boxes"
            ]
            assert all(box["score"] >= threshold for box in boxes), (
                f"a box scored below the requested threshold {threshold}"
            )

    def test_raising_the_threshold_never_adds_boxes(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Monotonicity, on identical features — the seed is what makes it comparable."""
        image = write_image(tmp_path / "a.png")
        instance = add_detector()

        counts = []
        for threshold in (0.0, 0.5, 0.9, 1.0):
            torch.manual_seed(1234)
            counts.append(
                len(propose(client, image, instance, score_threshold=threshold).json()["boxes"])
            )

        assert counts == sorted(counts, reverse=True), f"not monotonic: {counts}"


class TestRefusals:
    def test_a_classifier_is_refused_with_a_usable_reason(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """An empty list would read as "found nothing" — the opposite of what happened."""
        image = write_image(tmp_path / "a.png")
        response = propose(client, image, add_classifier())

        assert response.status_code == 409
        message = response.json()["error"]["message"]
        assert "labels" in message
        assert "Inference Viewer" in message

    def test_a_segmentation_head_is_refused(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        image = write_image(tmp_path / "a.png")
        response = propose(client, image, add_segmenter())

        assert response.status_code == 409
        assert "masks" in response.json()["error"]["message"]

    def test_an_unknown_head_is_404(self, client: TestClient, tmp_path: Path) -> None:
        image = write_image(tmp_path / "a.png")
        assert propose(client, image, "does-not-exist").status_code == 404

    def test_a_head_from_another_backbone_is_409_not_404(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """A 404 here would say "no such head" about a head the user can see listed.

        Exactly 409, not "404 or 409": heads are resolved before the backbone's
        capabilities are read, so the mismatch is reported rather than the fact that
        dinov2-base happens not to be installed. A loose assertion would pass either way
        and hide it if that order ever flipped.
        """
        image = write_image(tmp_path / "a.png")
        response = propose(client, image, add_detector(), backbone_id="dinov2-base")

        assert response.status_code == 409
        assert "dinov2-small" in response.json()["error"]["message"]

    def test_a_missing_image_is_404(self, client: TestClient) -> None:
        assert propose(client, "/nope/missing.png", add_detector()).status_code == 404

    def test_a_non_image_file_is_415(self, client: TestClient, tmp_path: Path) -> None:
        junk = tmp_path / "notes.txt"
        junk.write_text("not an image")
        assert propose(client, str(junk), add_detector()).status_code == 415

    def test_an_out_of_range_threshold_is_422(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        image = write_image(tmp_path / "a.png")
        assert propose(client, image, add_detector(), score_threshold=2.0).status_code == 422
