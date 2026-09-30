"""The parameter catalogue (doc 99): honest defaults, refusals that name the knob."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import fields

import pytest
from fastapi.testclient import TestClient

from app.api.v1.finetune_jobs import StartRequest
from app.api.v1.training import TrainingRequest
from app.finetune.adapter import FinetuneSettings
from app.main import create_app
from app.ml.training.config import TrainingConfig
from app.params import FAMILIES, family_for
from app.params.heads import HEAD


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


class TestResolve:
    def test_fills_every_default(self) -> None:
        resolved = HEAD.resolve({})
        assert resolved == HEAD.defaults()
        assert resolved["epochs"] == 20

    def test_keeps_a_given_value(self) -> None:
        assert HEAD.resolve({"epochs": 7})["epochs"] == 7

    def test_refuses_an_unknown_key_by_name(self) -> None:
        """A misspelt option used to train silently with the default."""
        with pytest.raises(ValueError, match="unfreez_blocks"):
            family_for("sam2.1-hiera-small").resolve({"unfreez_blocks": 2})

    def test_out_of_range_names_label_term_and_range(self) -> None:
        with pytest.raises(ValueError, match=r"Rounds \(epochs\) must be between 1 and 1000"):
            HEAD.resolve({"epochs": 0})

    def test_a_whole_number_stays_whole(self) -> None:
        with pytest.raises(ValueError, match="whole number"):
            HEAD.resolve({"epochs": 2.5})
        assert isinstance(HEAD.resolve({"epochs": 3.0})["epochs"], int)

    def test_a_choice_must_be_offered(self) -> None:
        with pytest.raises(ValueError, match="constant, cosine"):
            HEAD.resolve({"lr_schedule": "linear"})

    def test_a_bool_is_not_a_number(self) -> None:
        with pytest.raises(ValueError, match="must be a number"):
            HEAD.resolve({"epochs": True})


class TestEveryParameterIsExplained:
    @pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f.family)
    def test_label_term_help_and_why(self, family: object) -> None:
        for parameter in family.parameters:  # type: ignore[attr-defined]
            assert parameter.label and parameter.term, parameter.key
            assert len(parameter.help) > 40, parameter.key
            assert len(parameter.why) > 20, parameter.key

    @pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f.family)
    def test_the_default_passes_its_own_check(self, family: object) -> None:
        for parameter in family.parameters:  # type: ignore[attr-defined]
            assert parameter.check(parameter.default) == parameter.default

    @pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f.family)
    def test_rounds_and_learning_speed_are_basic(self, family: object) -> None:
        for key in ("epochs", "learning_rate"):
            assert family.get(key).level == "basic"  # type: ignore[attr-defined]


class TestDefaultsAreTheRunningCode:
    def test_head_defaults_match_training_config(self) -> None:
        """A catalogue default that differs from the code is a lie in the ? popover."""
        config = {f.name: f.default for f in fields(TrainingConfig)}
        for key, default in HEAD.defaults().items():
            assert config[key] == default, key

    def test_head_defaults_match_the_request(self) -> None:
        request = TrainingRequest(head_type_id="h", backbone_id="b", dataset_ids=["d"])
        for key, default in HEAD.defaults().items():
            assert getattr(request, key) == default, key

    def test_save_best_only_is_not_offered(self) -> None:
        # It was never honoured (doc 99): the best round is always kept.
        assert "save_best_only" not in HEAD.defaults()


class TestFamilyFor:
    @pytest.mark.parametrize(
        ("model_id", "family"),
        [
            ("head", "head"),
            ("rf-detr-nano", "rf-detr"),
            ("sam2.1-hiera-small", "sam2"),
            ("sam3", "sam3"),
            ("dinov2-small-classification", "dino-backbone"),
            ("dinov3-vitb16-segmentation", "dino-backbone"),
        ],
    )
    def test_matches_like_the_adapters(self, model_id: str, family: str) -> None:
        assert family_for(model_id).family == family

    def test_unknown_is_a_lookup_error(self) -> None:
        with pytest.raises(LookupError):
            family_for("dinov2-small")


class TestRoutes:
    def test_lists_every_family(self, client: TestClient) -> None:
        body = client.get("/api/v1/training/parameters").json()
        assert [f["family"] for f in body] == [f.family for f in FAMILIES]

    def test_one_family_with_everything_the_form_needs(self, client: TestClient) -> None:
        body = client.get("/api/v1/training/parameters/sam2.1-hiera-small").json()
        assert body["family"] == "sam2"
        jitter = next(p for p in body["parameters"] if p["key"] == "box_jitter")
        assert jitter["label"] == "Box looseness" and jitter["term"] == "box jitter"
        assert jitter["default"] == 0.1 and jitter["level"] == "advanced"
        assert jitter["minimum"] == 0.0 and jitter["maximum"] == 0.5
        assert jitter["help"] and jitter["why"]

    def test_choices_are_listed(self, client: TestClient) -> None:
        body = client.get("/api/v1/training/parameters/head").json()
        schedule = next(p for p in body["parameters"] if p["key"] == "lr_schedule")
        assert [c["value"] for c in schedule["choices"]] == ["constant", "cosine"]

    def test_unknown_model_is_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/training/parameters/nope").status_code == 404

    def test_finetune_refuses_an_unknown_option_as_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/finetune/jobs",
            json={
                "finetune_id": "sam2.1-hiera-small",
                "dataset_ids": ["x"],
                "name": "n",
                "options": {"unfreez_blocks": 2},
            },
        )
        assert response.status_code == 422
        assert "unfreez_blocks" in response.json()["error"]["message"]

    def test_finetune_refuses_out_of_range_rounds_as_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/finetune/jobs",
            json={"finetune_id": "sam3", "dataset_ids": ["x"], "name": "n", "epochs": 0},
        )
        assert response.status_code == 422

    def test_training_refuses_an_unknown_schedule(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/training/jobs",
            json={
                "head_type_id": "linear-classifier",
                "backbone_id": "dinov2-small",
                "dataset_ids": ["x"],
                "lr_schedule": "linear",
            },
        )
        assert response.status_code == 422


class TestFinetuneDefaultsPerModel:
    """One default for all (10 rounds, 1e-4) was wrong for SAM 3 and the backbones."""

    def _settings(self, finetune_id: str, **given: object) -> FinetuneSettings:
        request = StartRequest(finetune_id=finetune_id, dataset_ids=["d"], name="n", **given)
        return request.settings()

    def test_omitted_values_come_from_the_model(self) -> None:
        assert self._settings("sam3").epochs == 4
        # Doc 108: 1e-4 made SAM 3 worse than its base; 1e-5 made it better.
        assert self._settings("sam3").learning_rate == 1e-5
        assert self._settings("dinov2-small-classification").learning_rate == 1e-3
        assert self._settings("rf-detr-nano").epochs == 10

    def test_every_option_is_filled_for_provenance(self) -> None:
        settings = self._settings("sam2.1-hiera-small", options={"box_jitter": 0.2})
        assert settings.options["box_jitter"] == 0.2
        assert settings.options["focal_weight"] == 20.0
        recorded = settings.as_parameters()
        assert recorded["epochs"] == 6 and recorded["box_jitter"] == 0.2
