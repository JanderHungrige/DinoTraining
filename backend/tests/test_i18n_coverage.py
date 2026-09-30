"""Is the German catalogue complete? (doc 113, business rule 3)

Two proofs. The static catalogues are fetched in English and in German, and every text
field must differ. The audit's rules are fired over hand-built facts, and every finding's
title, what, why and action must translate. An English text changed in the code without its
German fails here, rather than surfacing in English to a German reader.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient

from app.i18n.middleware import TEXT_FIELDS
from app.i18n.translate import translate_text
from app.prep.finding_types import AuditContext, Finding
from app.prep.findings import RULES, evaluate
from app.prep.intake_findings import intake_findings
from app.prep.profiles import get_profile
from app.prep.stats import AnnotationFacts, DatasetFacts, ImageFacts
from app.prep.task_facts import MaskFacts, PhraseFacts
from tests.datasets_api_testkit import dataset_client
from tests.test_prep_findings import facts

DE = {"Accept-Language": "de"}
#: Product names, model-id lists and parameter names: the same in every language.
SAME_IN_GERMAN = {
    "RF-DETR",
    "RF-DETR (nano)",
    "SAM 2.1",
    "SAM 2.1 (small)",
    "SAM 3",
    "rf-detr-nano, rf-detr-small, rf-detr-base",
    "sam2.1-hiera-small, sam2.1-hiera-base-plus, sam2.1-hiera-large",
    "sam3",
    "num_negatives",
    "num_cross_negatives",
}


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for ac in dataset_client(tmp_path, monkeypatch):
        yield ac


def text_pairs(en: Any, de: Any, where: str = "", key: str = "") -> Iterator[tuple[str, str, str]]:
    """(where, English, German) for every string under a text field, walked in step."""
    if isinstance(en, dict):
        assert isinstance(de, dict) and en.keys() == de.keys(), where
        for k in en:
            yield from text_pairs(en[k], de[k], f"{where}.{k}", k)
    elif isinstance(en, list):
        assert isinstance(de, list) and len(en) == len(de), where
        for i, (a, b) in enumerate(zip(en, de, strict=True)):
            yield from text_pairs(a, b, f"{where}[{i}]", key)
    elif isinstance(en, str) and key in TEXT_FIELDS:
        yield where, en, de
    else:
        assert en == de, f"{where} is not a text field and must not change"


@pytest.mark.parametrize(
    "route",
    [
        "/api/v1/finetune/requirements",
        "/api/v1/training/parameters",
        "/api/v1/annotation-targets",
        "/api/v1/prep/targets",
    ],
)
async def test_every_static_text_is_german(client: AsyncClient, route: str) -> None:
    english = (await client.get(route)).json()
    german = (await client.get(route, headers=DE)).json()
    pairs = list(text_pairs(english, german))
    assert len(pairs) > 10
    untranslated = [
        f"{where}: {en!r}"
        for where, en, de in pairs
        if en == de and en.strip() and en not in SAME_IN_GERMAN
    ]
    assert untranslated == []


def _images(count: int, sequence: str | None = None) -> list[ImageFacts]:
    return [ImageFacts(i, f"/i/{i}.jpg", 1200, 800, sequence, i) for i in range(count)]


def _box(image: int, cls: str, side: float, label: str = "positive", x: float = 0) -> Any:
    return AnnotationFacts(image, "box", label, cls, cls, side, side, x, 0)


def _contexts() -> list[AuditContext]:
    """Contexts that fire every rule, and each branch whose wording differs."""
    thin = [_box(i, "pawn", 200) for i in range(15)] + [_box(0, "bishop", 200)]
    spelled = [_box(i, "traffic-light" if i % 2 else "traffic lights", 200) for i in range(120)]
    unclear = [_box(i, "car", 200, "unclear" if i % 3 else "positive") for i in range(120)]
    masks = [
        AnnotationFacts(i, "mask", "positive", "car", "car", 200, 200, 0, 0) for i in range(120)
    ]
    tiny_masks = [
        AnnotationFacts(i, "mask", "positive", "ring", "ring", 5, 5, 0, 0) for i in range(120)
    ]
    frames = DatasetFacts(
        "d",
        _images(3, "ride.mp4"),
        [_box(0, "signal", 10, x=20), _box(1, "light", 10, x=21), _box(2, "light", 10, x=21)],
    )
    return [
        AuditContext(
            DatasetFacts("d", _images(15), thin),
            None,
            unreadable=["/i/gone.jpg"],
            copy_groups=[["/i/1.jpg", "/i/2.jpg"]],
            scene_groups=[["/i/3.jpg", "/i/4.jpg"]],
        ),
        AuditContext(DatasetFacts("d", _images(120), spelled), None),
        AuditContext(DatasetFacts("d", _images(120), unclear), None),
        AuditContext(DatasetFacts("d", _images(120), [_box(0, "car", 200)]), None),
        AuditContext(frames, None),
        AuditContext(
            facts(150, [(i, "signal", 11) for i in range(150)]), get_profile("rf-detr-nano")
        ),
        AuditContext(
            facts(150, [(i, "signal", 30) for i in range(150)]), get_profile("rf-detr-nano")
        ),
        AuditContext(facts(120, [(i, "car", 200) for i in range(120)]), get_profile("sam3")),
        AuditContext(DatasetFacts("d", _images(120), masks), get_profile("rf-detr-nano")),
        AuditContext(
            facts(2, [(0, "cat", 200), (0, "dog", 200), (1, "cat", 200)]),
            get_profile("head-classification-dinov2"),
        ),
        AuditContext(
            DatasetFacts("d", _images(120), tiny_masks),
            get_profile("sam2.1-hiera-small"),
            masks=MaskFacts(10, [("/a.png", "ring", 3)], [("/b.png", "ring", "blob", 0.91)]),
        ),
        AuditContext(
            facts(1, []),
            get_profile("sam3"),
            phrases=PhraseFacts([("ring", 139, 0), ("blob", 12, 2)], 70, 69, 1, 0),
        ),
        AuditContext(
            facts(1, []), get_profile("sam3"), phrases=PhraseFacts([("ring", 60, 2)], 5, 5, 0)
        ),
    ]


def _untranslated(finding: Finding) -> list[str]:
    fields = {"title": finding.title, "why": finding.why, "action": finding.action}
    # Spellings list the user's own class names; there is nothing else to translate.
    if finding.id != "class-spellings":
        fields["what"] = finding.what
    return [
        f"{finding.id}.{name}: {text!r}"
        for name, text in fields.items()
        if translate_text(text, "de") == text
    ]


def test_every_audit_rule_speaks_german() -> None:
    findings = [finding for ctx in _contexts() for finding in evaluate(ctx)]
    assert len({f.id for f in findings}) == len(RULES)
    assert [problem for f in findings for problem in _untranslated(f)] == []


def test_the_objects_too_small_action_is_german_in_every_branch() -> None:
    actions = {
        f.action for ctx in _contexts() for f in evaluate(ctx) if f.id == "objects-too-small"
    }
    assert len(actions) >= 3
    for action in actions:
        german = translate_text(action, "de")
        assert all(word not in german for word in ("Tiling", "Cut into", "Whole images")), german


def _report(convention: str | None) -> Any:
    evidence = SimpleNamespace(boxes=5, valid_as_xywh=0.5, valid_as_xyxy=0.4)
    file = SimpleNamespace(
        source="train",
        evidence=evidence,
        missing_images=["a.jpg"],
        images=10,
        size_mismatches=["b.jpg"],
    )
    return SimpleNamespace(
        files=[file],
        convention=convention,
        proposed_class_map={"glases": "glass"},
        has_source_split=True,
    )


def test_every_intake_finding_speaks_german() -> None:
    findings = [*intake_findings(_report(None)), *intake_findings(_report("xyxy"))]
    assert len({f.id for f in findings}) == 6
    assert [problem for f in findings for problem in _untranslated(f)] == []
