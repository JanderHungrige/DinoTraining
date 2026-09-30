"""Augmentation moves targets exactly as it moves the picture (doc 87)."""

from __future__ import annotations

import random
from dataclasses import replace

import numpy as np
import pytest
import torch
from PIL import Image, ImageDraw

from app.datasets.rle import rle_decode, rle_encode
from app.ml.augment import PRESETS, Variant, augment, meaning_guard
from app.ml.training.augmented import Variants, augment_sample, copies_that_fit, preset_for
from app.ml.training.config import TrainingConfig
from app.ml.training.preparation import preset_name
from app.ml.training.samples import MaskTarget, TrainingSample

COLOURS = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
BOXES = [(20.0, 30.0, 40.0, 20.0), (150.0, 100.0, 30.0, 60.0), (90.0, 10.0, 10.0, 10.0)]


def scene() -> Variant:
    """A 240x180 grey picture with three coloured objects, each with its own mask."""
    image = Image.new("RGB", (240, 180), (128, 128, 128))
    draw = ImageDraw.Draw(image)
    masks = []
    for (x, y, w, h), colour in zip(BOXES, COLOURS, strict=True):
        draw.rectangle((x, y, x + w - 1, y + h - 1), fill=colour)
        mask = np.zeros((180, 240), dtype=bool)
        mask[int(y) : int(y + h), int(x) : int(x + w)] = True
        masks.append(mask)
    return Variant(image, list(BOXES), masks)


@pytest.mark.parametrize("preset_id", ["general", "outdoor", "microscopy", "documents"])
@pytest.mark.parametrize("seed", range(12))
def test_every_box_and_mask_lands_on_its_object(preset_id: str, seed: int) -> None:
    geometry_only = replace(PRESETS[preset_id], colour=0.0, blur=0.0, noise=0.0)
    changed = augment(scene(), geometry_only, random.Random(seed))
    pixels = np.asarray(changed.image)
    height, width = pixels.shape[:2]
    for (x, y, w, h), mask, colour in zip(changed.boxes, changed.masks, COLOURS, strict=True):
        # A crop never cuts an object: it is whole and inside the picture.
        assert 0 <= x and 0 <= y and x + w <= width and y + h <= height
        assert {round(w), round(h)} in ({10}, {20, 40}, {30, 60})
        inside = pixels[int(y) : int(y + h), int(x) : int(x + w)]
        assert (inside == colour).all(axis=-1).all(), (preset_id, seed)
        assert mask.shape == (height, width)
        assert (pixels[mask] == colour).all()
        assert mask.sum() == round(w * h)


def test_colour_changes_leave_the_targets_alone() -> None:
    colour_only = replace(PRESETS["outdoor"], crop=1.0)
    changed = augment(scene(), colour_only, random.Random(3))
    assert changed.boxes == list(BOXES)
    assert not np.array_equal(np.asarray(changed.image), np.asarray(scene().image))


def test_presets_for_signs_and_text_never_mirror() -> None:
    assert PRESETS["outdoor"].hflip == 0 and PRESETS["documents"].hflip == 0
    guarded, risky = meaning_guard(PRESETS["general"], ["car", "stop sign", "left arrow"])
    assert risky == ["stop sign", "left arrow"]
    assert guarded.hflip == 0 and guarded.crop == PRESETS["general"].crop
    # Whole words only: "platelets" is not a "plate" (found live on blood cells).
    assert meaning_guard(PRESETS["general"], ["platelets", "signal_pole", "Stop Signs"])[1] == [
        "signal_pole",
        "Stop Signs",
    ]
    same, none = meaning_guard(PRESETS["general"], ["car", "bus"])
    assert same == PRESETS["general"] and none == []


def test_a_training_sample_is_moved_whole() -> None:
    mask = np.zeros((180, 240), dtype=bool)
    mask[30:50, 20:60] = True
    counts, size = rle_encode(mask)
    sample = TrainingSample(
        "/s.png",
        240,
        180,
        targets=((1, *BOXES[0]), (0, *BOXES[1])),
        ignore_regions=(BOXES[2],),
        masks=(MaskTarget(class_index=1, size=size, counts=tuple(counts)),),
    )
    turn = replace(PRESETS["microscopy"], colour=0.0, blur=0.0, hflip=0.0, vflip=0.0)
    for seed in range(8):
        image, moved = augment_sample(scene().image, sample, turn, random.Random(seed))
        assert (moved.width, moved.height) == image.size
        assert [t[0] for t in moved.targets] == [1, 0]  # labels stay with their boxes
        assert len(moved.ignore_regions) == 1
        decoded = rle_decode(list(moved.masks[0].counts), moved.masks[0].size)
        x, y, w, h = moved.targets[0][1:]
        assert decoded.sum() == 800
        assert decoded[int(y) : int(y + h), int(x) : int(x + w)].all()


def test_each_visit_is_the_original_or_one_of_its_copies() -> None:
    variants = Variants(of={0: [10, 11]}, copies=2)
    seen = {variants.pick((0, 1), random.Random(e))[0] for e in range(60)}
    assert seen == {0, 10, 11}
    assert variants.pick((1,), random.Random(0)) == (1,)


def test_copies_are_cut_to_the_memory_budget() -> None:
    class Features:
        cls = torch.zeros(0)
        patches = torch.zeros(1024 * 1024 * 64)  # 256 MB

    cache = [(Features(), {})] * 4
    assert copies_that_fit(cache, 4, 8) == 2  # 3 GB − 1 GB used, 1 GB per round of copies
    assert copies_that_fit(cache, 4, 1) == 1


def test_the_old_augment_flag_means_the_general_preset() -> None:
    base = {"head_type_id": "linear-classifier", "backbone_id": "b", "dataset_ids": ("d",)}
    assert preset_name(TrainingConfig(**base, augment=True)) == "general"  # type: ignore[arg-type]
    assert preset_name(TrainingConfig(**base)) == "none"  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Unknown augmentation preset"):
        preset_for("sepia", [])
