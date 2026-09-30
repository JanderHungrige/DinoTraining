"""A train/validation/test split that cannot leak (doc 84).

Doc 11's split shuffled *images*. That is right for independent photos and wrong for
everything this app now produces in bulk: consecutive video frames (doc 73) and several
photos of one scene (doc 81). On 10 Hz rail video it inflated a reported mAP by 42 % (doc
49), because the test frames were near-copies of training frames.

So the unit of splitting is a **group**, and a group never straddles two sides:

* **a scene group** from the last audit: the same picture, whatever it is annotated with;
* **a segment of a sequence**: a video or folder cut into contiguous stretches. A whole
  video is not one group, or a dataset of one video could not be split at all. Where a
  segment on the validation or test side meets one on another side, the frames nearest the
  boundary become **buffer**, used by no side, because they are near-copies of the frames
  across the line;
* otherwise an image on its own.

Groups are assigned greedily, largest first, to whichever side is furthest below its
target share *for the classes the group contains*, so rare classes reach every side where
they can. The result is stored in `images.split` and never reshuffled: evaluation is
reproducible, and a recipe (doc 88) records it.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from app.prep.stats import DatasetFacts

SIDES = ("train", "val", "test")
BUFFER = "buffer"
#: Segments per sequence. Ten is enough for a 70/20/10 split to find a home for each side.
SEGMENTS_PER_SEQUENCE = 10
#: A segment shorter than this is joined to its neighbour: a one-frame segment on the
#: validation side is nothing but buffer.
MIN_SEGMENT_FRAMES = 5
#: A step between annotated frames this many times the usual step is a gap: the stretches
#: on either side were annotated separately, and are a natural boundary that needs no buffer.
GAP_FACTOR = 3


@dataclass
class Group:
    image_ids: list[int]
    classes: Counter[str] = field(default_factory=Counter)


class _Union:
    def __init__(self, ids: list[int]) -> None:
        self.parent = {i: i for i in ids}

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def join(self, ids: list[int]) -> None:
        roots = [self.find(i) for i in ids if i in self.parent]
        for other in roots[1:]:
            self.parent[other] = roots[0]


def _sequences(facts: DatasetFacts) -> dict[str, list[tuple[int, int]]]:
    """(frame index, image id) per sequence, in frame order."""
    frames: defaultdict[str, list[tuple[int, int]]] = defaultdict(list)
    for image in facts.images:
        if image.sequence is not None:
            frames[image.sequence].append((image.frame_index or 0, image.id))
    return {key: sorted(value) for key, value in frames.items()}


def _stretches(frames: list[tuple[int, int]]) -> list[list[int]]:
    """Image ids in runs of frames annotated together, split where the step jumps.

    Found live (2026-09-29): frames 0-4 and 16-20 of one clip were treated as neighbours,
    and the buffer between them took every validation frame.
    """
    if not frames:
        return []
    steps = sorted(b[0] - a[0] for a, b in zip(frames, frames[1:], strict=False))
    usual = max(1, steps[len(steps) // 2]) if steps else 1
    runs: list[list[int]] = [[frames[0][1]]]
    for previous, (index, image_id) in zip(frames, frames[1:], strict=False):
        if index - previous[0] > GAP_FACTOR * usual:
            runs.append([])
        runs[-1].append(image_id)
    return runs


def _segment(stretch: list[int], sequence_length: int) -> list[list[int]]:
    size = max(MIN_SEGMENT_FRAMES, math.ceil(sequence_length / SEGMENTS_PER_SEQUENCE))
    pieces = [stretch[i : i + size] for i in range(0, len(stretch), size)]
    if len(pieces) > 1 and len(pieces[-1]) < MIN_SEGMENT_FRAMES:
        pieces[-2].extend(pieces.pop())
    return pieces


def build_groups(facts: DatasetFacts, scene_groups: list[list[str]]) -> list[Group]:
    ids = [image.id for image in facts.images]
    union = _Union(ids)
    by_path = {image.path: image.id for image in facts.images}
    for scene in scene_groups:
        union.join([by_path[p] for p in scene if p in by_path])
    for frames in _sequences(facts).values():
        for stretch in _stretches(frames):
            for segment in _segment(stretch, len(frames)):
                union.join(segment)
    members: defaultdict[int, list[int]] = defaultdict(list)
    for i in ids:
        members[union.find(i)].append(i)
    classes: defaultdict[int, Counter[str]] = defaultdict(Counter)
    for annotation in facts.positives():
        classes[annotation.image_id][annotation.cls] += 1
    groups = []
    for image_ids in members.values():
        counted: Counter[str] = Counter()
        for i in image_ids:
            counted.update(classes[i])
        groups.append(Group(image_ids=sorted(image_ids), classes=counted))
    return groups


def assign(groups: list[Group], fractions: dict[str, float], seed: int) -> dict[int, str]:
    """Group-wise, largest first, to the side furthest below its share for these classes."""
    rng = random.Random(seed)
    ordered = groups[:]
    rng.shuffle(ordered)  # ties broken reproducibly, not by insertion order
    ordered.sort(key=lambda g: len(g.image_ids), reverse=True)
    total_images = sum(len(g.image_ids) for g in groups)
    total_classes: Counter[str] = Counter()
    for group in groups:
        total_classes.update(group.classes)
    placed_images = dict.fromkeys(SIDES, 0)
    placed_classes: dict[str, Counter[str]] = {side: Counter() for side in SIDES}

    def deficit(side: str, group: Group) -> float:
        want = fractions[side]
        if want <= 0:
            return -math.inf
        image_gap = want - placed_images[side] / max(1, total_images)
        class_gap = sum(
            want - placed_classes[side][name] / total_classes[name] for name in group.classes
        ) / max(1, len(group.classes))
        return image_gap + class_gap

    result: dict[int, str] = {}
    for group in ordered:
        side = max(SIDES, key=lambda s: deficit(s, group))
        placed_images[side] += len(group.image_ids)
        placed_classes[side].update(group.classes)
        for i in group.image_ids:
            result[i] = side
    return result


def mark_buffers(facts: DatasetFacts, sides: dict[int, str]) -> dict[int, str]:
    """Frames beside a boundary with another side, on the evaluation side, become buffer.

    Only inside a stretch: across a gap the frames are not near-copies. And never a whole
    run: a validation run of three frames keeps at least two, since a side emptied by its
    own buffer is worse than a slightly closer neighbour.
    """
    marked = dict(sides)
    for frames in _sequences(facts).values():
        width = max(1, math.ceil(len(frames) / SEGMENTS_PER_SEQUENCE / 10))
        for stretch in _stretches(frames):
            _buffer_stretch(stretch, sides, marked, width)
    return marked


def _buffer_stretch(
    stretch: list[int], sides: dict[int, str], marked: dict[int, str], width: int
) -> None:
    """Positions, not `list.index`: a 10-minute clip is 18,000 frames."""
    runs: list[list[int]] = []
    for position, image_id in enumerate(stretch):
        if position and sides[image_id] == sides[stretch[position - 1]]:
            runs[-1].append(image_id)
        else:
            runs.append([image_id])
    for index, run in enumerate(runs):
        if sides[run[0]] == "train":
            continue
        ends = (index > 0, index < len(runs) - 1)
        room = (len(run) - 1) // max(1, sum(ends))
        take = min(width, room)
        if take <= 0:
            continue
        if ends[0]:
            for image_id in run[:take]:
                marked[image_id] = BUFFER
        if ends[1]:
            for image_id in run[-take:]:
                marked[image_id] = BUFFER


__all__ = ["BUFFER", "SIDES", "Group", "assign", "build_groups", "mark_buffers"]
