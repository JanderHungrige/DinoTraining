"""Which queries a picture teaches SAM 3 (doc 108)."""

from __future__ import annotations

import random
from collections import Counter

import numpy as np

from app.finetune.adapters.sam2 import _clicks
from app.finetune.adapters.sam3_queries import GENERIC_POOL, QuerySettings, describe, plan_queries
from app.finetune.phrase_data import PhraseDef, PhraseTable
from app.ml.training.samples import MaskTarget, TrainingSample

NAMES = ("car", "bus")
NONE = QuerySettings(num_negatives=0)


def sample(path: str, *classes: int) -> TrainingSample:
    masks = tuple(MaskTarget(c, (4, 4), (i, 1, 15 - i)) for i, c in enumerate(classes))
    return TrainingSample(path=path, width=4, height=4, masks=masks, segmented=True)


def kinds(queries: list) -> list[tuple[str, str, tuple[int, ...]]]:  # type: ignore[type-arg]
    return [(q.text, q.kind, q.masks) for q in queries]


def plan(s: TrainingSample, table: PhraseTable, settings: QuerySettings = NONE, **kw: bool) -> list:  # type: ignore[type-arg]
    return plan_queries(s, NAMES, table, settings, random.Random(0), **kw)


class TestLegacy:
    def test_every_class_is_asked_and_an_absent_one_teaches_none_here(self) -> None:
        """Before any check exists, exactly the old behaviour."""
        assert kinds(plan(sample("/a", 0, 0), PhraseTable())) == [
            ("car", "positive", (0, 1)),
            ("bus", "cross", ()),
        ]


class TestChecked:
    """A picture saved before car and bus existed (doc 117): only hand checks teach."""

    def table(self, **statuses: str) -> PhraseTable:
        return PhraseTable(
            phrases={"car": PhraseDef("car", "car"), "bus": PhraseDef("bus", "bus")},
            statuses={"/a": statuses} if statuses else {},
            unknown={"/a": {"car", "bus"}},
        )

    def test_only_checked_pairs_teach(self) -> None:
        assert kinds(plan(sample("/a", 0), self.table(car="complete"))) == [
            ("car", "positive", (0,))
        ]

    def test_absent_is_an_explicit_negative(self) -> None:
        assert kinds(plan(sample("/a", 0), self.table(car="complete", bus="absent"))) == [
            ("car", "positive", (0,)),
            ("bus", "absent", ()),
        ]

    def test_an_unchecked_picture_teaches_nothing(self) -> None:
        assert plan(sample("/a", 0), self.table()) == []

    def test_all_marked_without_an_outline_is_skipped_not_guessed(self) -> None:
        assert plan(sample("/a"), self.table(car="complete")) == []

    def test_a_rejection_is_a_negative_unless_turned_off(self) -> None:
        table = self.table()
        table.rejected = {"/a": {"bus"}}
        assert kinds(plan(sample("/a", 0), table)) == [("bus", "rejected", ())]
        off = QuerySettings(num_negatives=0, rejected_as_negatives=False)
        assert plan(sample("/a", 0), table, off) == []

    def test_look_alikes_are_negatives_where_the_phrase_is_all_marked(self) -> None:
        table = self.table(car="complete")
        table.phrases["car"] = PhraseDef("car", "car", confusable=("van",))
        assert ("van", "confusable", ()) in kinds(plan(sample("/a", 0), table))

    def test_no_look_alike_negative_where_an_outline_of_the_phrase_was_rejected(self) -> None:
        """Jan's flames: a rejected 'flame' outline is likely the reflection itself, so
        'flame reflection: none here' would be a lie on that picture. The positive
        'flame' query with only the true outlines already teaches the difference."""
        table = self.table(car="complete")
        table.phrases["car"] = PhraseDef("car", "car", confusable=("van",))
        table.rejected = {"/a": {"car"}}
        planned = kinds(plan(sample("/a", 0), table))
        assert ("car", "positive", (0,)) in planned
        assert not [q for q in planned if q[1] == "confusable"]

    def test_a_linked_phrase_answers_with_its_outlines(self) -> None:
        table = self.table(car="complete")
        table.phrases["red car"] = PhraseDef("red car", "car")
        table.statuses["/a"]["red car"] = "complete"
        s = sample("/a", 0, 0)
        table.linked = {"/a": {s.masks[1].counts: ("red car",)}}
        assert ("red car", "positive", (1,)) in kinds(plan(s, table))


class TestSavedMeansComplete:
    """Doc 117 (Jan, 2026-09-30): a saved picture is complete for the classes that existed
    when it was saved; checking by hand is only the exception."""

    def test_a_saved_picture_teaches_without_any_check(self) -> None:
        table = PhraseTable(phrases={"car": PhraseDef("car", "car")})
        assert kinds(plan(sample("/a", 0), table)) == [
            ("car", "positive", (0,)),
            ("bus", "cross", ()),
        ]

    def test_a_check_elsewhere_no_longer_takes_the_negatives_away(self) -> None:
        """Doc 108's checked mode left every unchecked picture out once one was checked."""
        table = PhraseTable(statuses={"/other": {"car": "complete", "bus": "absent"}})
        assert kinds(plan(sample("/a", 0), table)) == [
            ("car", "positive", (0,)),
            ("bus", "cross", ()),
        ]

    def test_a_class_added_later_is_left_out_on_older_pictures_only_for_it(self) -> None:
        """m10 made after this picture was saved: no 'no bus here', car still teaches."""
        table = PhraseTable(unknown={"/a": {"bus"}})
        assert kinds(plan(sample("/a", 0), table)) == [("car", "positive", (0,))]

    def test_a_sub_phrase_follows_its_class(self) -> None:
        table = PhraseTable(
            phrases={"red car": PhraseDef("red car", "car")}, unknown={"/a": {"car"}}
        )
        s = sample("/a", 0)
        table.linked = {"/a": {s.masks[0].counts: ("red car",)}}
        assert not [q for q in kinds(plan(s, table)) if q[0] == "red car"]


class TestWordingsAndNegatives:
    def test_one_wording_per_round_or_all_of_them(self) -> None:
        table = PhraseTable(
            phrases={"car": PhraseDef("car", "car", variants=("automobile", "auto"))}
        )
        s = sample("/a", 0)
        words = {
            q.text
            for seed in range(20)
            for q in plan_queries(s, NAMES, table, NONE, random.Random(seed))
            if q.kind == "positive"
        }
        assert words == {"car", "automobile", "auto"}
        every = QuerySettings(num_negatives=0, all_variations=True)
        assert [q.text for q in plan(s, table, every) if q.kind == "positive"] == [
            "car",
            "automobile",
            "auto",
        ]
        # Evaluation always asks the phrase itself, so base and fine-tuned are compared fairly.
        assert [q.text for q in plan(s, table, every, evaluation=True) if q.kind == "positive"] == [
            "car"
        ]

    def test_generic_negatives_leave_out_the_dataset_s_own_words(self) -> None:
        queries = plan(sample("/a", 0), PhraseTable(), QuerySettings(num_negatives=10))
        generic = [q.text for q in queries if q.kind == "generic"]
        assert len(generic) == 10 and set(generic) <= set(GENERIC_POOL)
        assert "car" not in generic and "bus" not in generic
        assert not [
            q
            for q in plan(
                sample("/a", 0), PhraseTable(), QuerySettings(num_negatives=10), evaluation=True
            )
            if q.kind == "generic"
        ]

    def test_cross_negatives_are_capped_only_above_fifty_phrases(self) -> None:
        many = tuple(f"class {i}" for i in range(60))
        s = sample("/a", 0)
        capped = plan_queries(
            s,
            many,
            PhraseTable(),
            QuerySettings(num_negatives=0, num_cross_negatives=2),
            random.Random(0),
        )
        assert Counter(q.kind for q in capped) == Counter({"positive": 1, "cross": 2})

    def test_the_job_note_says_what_was_trained(self) -> None:
        note = describe(Counter({"positive": 140, "generic": 420, "absent": 20}), rounds=2)
        expected = (
            "SAM 3 trained on 70 positive queries and 220 negatives per round: "
            "10 absent, 0 cross, 0 rejected, 0 confusable, 210 generic."
        )
        assert note == expected


def test_sam2_clicks_land_inside_the_outline() -> None:
    mask = np.zeros((20, 20), dtype=bool)
    mask[5:8, 10:14] = True
    for x, y in _clicks(mask, 5, random.Random(1)):
        assert mask[int(y), int(x)]


def test_the_adapters_read_only_keys_the_catalogue_has() -> None:
    """Found live (doc 108): a setting the adapter reads but the catalogue lacks fails the
    job with a bare KeyError after it started. Every key read is checked here."""
    from app.finetune.adapter import FinetuneSettings
    from app.finetune.adapters.sam2 import Sam2Knobs
    from app.finetune.adapters.sam3 import query_settings
    from app.finetune.adapters.sam3_loss import LossWeights

    settings = FinetuneSettings()
    assert query_settings(settings) == QuerySettings()
    assert LossWeights.from_settings(settings) == LossWeights()
    assert Sam2Knobs.from_settings(settings).points == 1


def test_an_unclear_outline_is_never_a_negative_there() -> None:
    """Doc 109: the annotator's doubt is not 'none here'."""
    unclear = MaskTarget(1, (4, 4), (0, 1, 15))
    s = TrainingSample(
        path="/a",
        width=4,
        height=4,
        masks=sample("/a", 0).masks,
        ignore_masks=(unclear,),
        segmented=True,
    )
    assert kinds(plan(s, PhraseTable())) == [("car", "positive", (0,))]
    table = PhraseTable(
        phrases={"car": PhraseDef("car", "car"), "bus": PhraseDef("bus", "bus")},
        statuses={"/a": {"bus": "absent"}},
    )
    assert ("bus", "absent", ()) not in kinds(plan(s, table))
