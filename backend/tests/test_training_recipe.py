"""Training reads the prepared data: exclusions, class map, stored split, tiles (doc 90)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.datasets.masks import MaskStore
from app.datasets.models import Box, ImageAnnotation
from app.datasets.store import DatasetStore
from app.ml.training.config import TrainingConfig
from app.ml.training.job import TrainingJob
from app.ml.training.preparation import UNPREPARED_NOTE, choose_split
from app.ml.training.samples import TrainingSample, build_samples
from app.ml.training.tiles import tile_samples
from app.prep.fixes import set_class_map, set_excluded
from app.prep.split_service import make_split


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[DatasetStore]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_connection()
    yield DatasetStore()
    reset_connection()
    get_settings.cache_clear()


def _dataset(store: DatasetStore) -> str:
    dataset_id = store.create("Pieces", None, False).id
    for i, cls in enumerate(["bishop", "white-bishop", "pawn", "blur", "pawn", "pawn"]):
        box = Box(label="positive", provenance="hand-drawn", prompt=cls, x=1, y=1, w=5, h=5)
        store.replace_image_boxes(
            dataset_id, ImageAnnotation(path=f"/p/{i}.jpg", width=50, height=50, boxes=[box])
        )
    return dataset_id


def test_training_reads_the_fixes_as_the_audit_did(store: DatasetStore) -> None:
    dataset_id = _dataset(store)
    set_excluded(dataset_id, ["/p/5.jpg"], True)
    set_class_map(dataset_id, {"bishop": "white-bishop", "blur": None})
    samples = build_samples(store, (dataset_id,), MaskStore())

    assert len(samples.samples) == 5  # the excluded picture is not trained on
    assert samples.class_names == ("pawn", "white-bishop")  # merged; "blur" left out
    blur = next(s for s in samples.samples if s.path == "/p/3.jpg")
    # Left out means ignored, not background: the object is really there.
    assert blur.targets == () and len(blur.ignore_regions) == 1


def test_a_recipe_run_uses_the_stored_split(store: DatasetStore) -> None:
    dataset_id = _dataset(store)
    make_split(dataset_id, val_fraction=0.34, test_fraction=0.17, seed=3)
    samples = build_samples(store, (dataset_id,), MaskStore()).samples
    sides = {s.path: s.split for s in samples}
    job = TrainingJob(
        job_id="j",
        config=TrainingConfig(
            head_type_id="dense-detector", backbone_id="b", dataset_ids=(dataset_id,), recipe_id="r"
        ),
    )
    split = choose_split(job, samples, len(samples))
    assert {samples[i].path for i in split.train} == {p for p, s in sides.items() if s == "train"}
    assert {samples[i].path for i in split.test} == {p for p, s in sides.items() if s == "test"}
    assert job.notes == []


def test_a_run_without_a_recipe_says_its_data_is_unprepared() -> None:
    job = TrainingJob(
        job_id="j",
        config=TrainingConfig(head_type_id="dense-detector", backbone_id="b", dataset_ids=("d",)),
    )
    choose_split(job, [TrainingSample("/a", 1, 1)] * 10, 10)
    assert job.notes == [UNPREPARED_NOTE]


def test_tiles_keep_whole_objects_ignore_cut_ones_and_cap_background() -> None:
    sample = TrainingSample(
        "/f.jpg",
        1000,
        500,
        targets=((0, 100, 100, 40, 40), (1, 470, 100, 60, 40)),  # the second straddles a seam
    )
    tiles = tile_samples([sample], 2, overlap=0.0)
    left = next(t for t in tiles if t.crop == (0, 0, 500, 500))
    assert left.targets[0] == (0, 100, 100, 40, 40)
    assert left.targets[1][0] == 1 and left.targets[1][3] == pytest.approx(30)  # half inside
    right = next(t for t in tiles if t.crop == (500, 0, 500, 500))
    assert right.targets == ((1, 0, 100, 30, 40),)
    # A box only a third inside a tile is ignored there, not taught as background.
    thin = TrainingSample("/g.jpg", 1000, 500, targets=((0, 480, 10, 60, 10),))
    halves = {t.crop: t for t in tile_samples([thin], 2, overlap=0.0)}
    assert halves[(0, 0, 500, 500)].targets == ()
    assert halves[(0, 0, 500, 500)].ignore_regions == ((480, 10, 20, 10),)
    empty = TrainingSample("/e.jpg", 1000, 1000, targets=((0, 10, 10, 20, 20),))
    kept = tile_samples([empty], 4, overlap=0.0)
    assert len(kept) == 2  # one tile with the object, one background tile


def test_a_test_side_without_objects_gives_a_note_not_a_zero() -> None:
    # Found live on OSDaR (doc 90): the leak-free split put no object on the test side,
    # and "test mAP 0.0" read as "the model finds nothing".
    import torch
    from torch import nn

    from app.ml.training.preparation import NO_TEST_OBJECTS_NOTE, score_test

    head = nn.Linear(2, 2)
    job = TrainingJob(
        job_id="j",
        config=TrainingConfig(head_type_id="dense-detector", backbone_id="b", dataset_ids=("d",)),
        best_state={k: v.clone() for k, v in head.state_dict().items()},
    )
    empty = {"positive": torch.zeros(1, 4, 4, dtype=torch.bool)}
    score_test(
        job, head, lambda: (0.0, [{}], [empty]), lambda o, p: o, lambda d, t: {"map": 0.0}, 14
    )
    assert job.test_metrics == {} and job.notes == [NO_TEST_OBJECTS_NOTE]

    full = {"positive": torch.ones(1, 4, 4, dtype=torch.bool)}
    score_test(
        job, head, lambda: (0.0, [{}], [full]), lambda o, p: o, lambda d, t: {"map": 0.5}, 14
    )
    assert job.test_metrics == {"map": 0.5}
