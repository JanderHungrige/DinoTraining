"""Tests for the model catalogue."""

from __future__ import annotations

import pytest

from app.ml.registry import MODELS, all_models, get_model, licence_url


class TestRegistry:
    def test_ids_are_unique(self) -> None:
        ids = [spec.id for spec in all_models()]
        assert len(ids) == len(set(ids))

    def test_lookup_returns_the_matching_spec(self) -> None:
        spec = get_model("dinov2-base")
        assert spec is not None
        assert spec.repo_id == "facebook/dinov2-base"

    def test_unknown_id_returns_none(self) -> None:
        assert get_model("does-not-exist") is None

    def test_traversal_id_returns_none(self) -> None:
        """The registry lookup is what turns a traversal attempt into a 404."""
        assert get_model("../../etc/passwd") is None

    def test_a_gated_model_never_carries_a_permissive_licence(self) -> None:
        """Was `test_only_dinov3_is_gated`, then a stricter both-ways version.

        The both-ways form asserted that an **ungated** entry is always Apache-2.0, and
        Wave 6 proved that false: Depth Anything V2 Base and Large are ungated *and*
        CC BY-NC 4.0. Anyone can download them; almost nobody may ship what they produce.
        That is exactly the belief doc 35 exists to correct, so the test that encoded it
        has been narrowed to the direction that is actually an invariant — a gate implies
        terms to accept, and an Apache-2.0 entry behind one would be a catalogue mistake.
        """
        gated = {spec.id for spec in all_models() if spec.gated}
        assert gated == {"dinov3-vitb16", "dinov3-vitl16", "sam3"}
        for spec in all_models():
            if spec.gated:
                assert spec.licence != "Apache-2.0", f"{spec.id} is gated but Apache-2.0"

    def test_gating_and_licensing_are_independent(self) -> None:
        """The pairing the previous test wrongly ruled out, pinned as real.

        If this ever holds no entries again, the catalogue has quietly gone back to
        "downloadable means usable" and doc 35's badge stops being reachable.
        """
        open_but_restricted = [
            spec.id for spec in all_models() if not spec.gated and spec.non_commercial
        ]
        assert open_but_restricted, "no ungated non-commercial entry — doc 35 is untested"

    def test_a_non_apache_licence_is_flagged_or_gated(self) -> None:
        """Nothing may be quietly restrictive: an entry is either gated (terms shown at
        download) or flagged non-commercial (badged in the card), never neither."""
        for spec in all_models():
            if spec.licence != "Apache-2.0":
                assert spec.gated or spec.non_commercial, (
                    f"{spec.id} is {spec.licence} but neither gated nor flagged"
                )

    def test_only_sam3_needs_a_manual_access_request(self) -> None:
        needing = {spec.id for spec in all_models() if spec.requires_access_request}
        assert needing == {"sam3"}

    def test_anything_needing_approval_is_also_gated(self) -> None:
        """An access request without a gate is incoherent, and would skip the token check."""
        for spec in all_models():
            if spec.requires_access_request:
                assert spec.gated

    def test_every_family_has_an_entry(self) -> None:
        families = {spec.family for spec in all_models()}
        assert families == {
            "grounding-dino",
            "dinov2",
            "dinov3",
            "sam2",
            "sam3",
            "depth-anything",
            "rf-detr",
        }

    def test_specs_are_immutable(self) -> None:
        """The catalogue is not user-editable; a frozen dataclass enforces that."""
        import dataclasses

        import pytest

        spec = MODELS["dinov2-base"]
        with pytest.raises(dataclasses.FrozenInstanceError):
            spec.repo_id = "attacker/evil-repo"  # type: ignore[misc]

    def test_every_spec_has_a_plausible_size(self) -> None:
        assert all(spec.approx_size_mb > 0 for spec in all_models())

    def test_every_spec_has_a_description(self) -> None:
        assert all(spec.description.strip() for spec in all_models())


class TestLicenceUrl:
    def test_points_at_the_models_own_repo(self) -> None:
        spec = MODELS["dinov3-vitl16"]
        assert licence_url(spec).endswith(spec.repo_id)

    def test_gated_models_get_distinct_urls(self) -> None:
        """Both DINOv3 cards once linked to the vitb16 gate — accepting it there
        still leaves vitl16 returning 403."""
        gated = [spec for spec in all_models() if spec.gated]
        urls = {licence_url(spec) for spec in gated}
        assert len(urls) == len(gated)


class TestNothingIsBundledOrAutoDownloaded:
    """Weights are never shipped in the installer and never fetched behind the user.

    The catalogue totals ~8 GB and SAM 3 alone is 3.2 GB, so an implicit download is the
    difference between a 30 MB install and an unusable one. Every loader must refuse
    rather than fetch, and the only place that may fetch is the admin-triggered job.
    """

    def test_only_the_download_manager_may_fetch(self) -> None:
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[1] / "app"
        offenders = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*.py")
            if "snapshot_download" in path.read_text(encoding="utf-8")
            and path.name != "downloads.py"
            # paths.py only mentions it in a comment about what it writes.
            and "snapshot_download(" in path.read_text(encoding="utf-8")
        ]
        assert offenders == [], f"implicit download reachable from: {offenders}"

    def test_every_loader_refuses_a_missing_model(
        self, tmp_path: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PIL import Image

        from app.core.config import get_settings
        from app.ml.backbone import load_backbone
        from app.ml.detector import load_detector
        from app.ml.errors import ModelNotInstalledError
        from app.ml.foundation.build import build_foundation, reset_cache
        from app.ml.segmenter import load_segmenter

        monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path))
        get_settings.cache_clear()
        reset_cache()
        try:
            for load, model_id in (
                (load_detector, "grounding-dino-tiny"),
                (load_segmenter, "sam2.1-hiera-small"),
                (load_segmenter, "sam3"),
                (load_backbone, "dinov2-small"),
            ):
                with pytest.raises(ModelNotInstalledError):
                    load(model_id)

            # Doc 36's loader is bound by the same rule. It refuses at `predict`, because
            # that is when it would otherwise reach `from_pretrained` and the network —
            # constructing it is deliberately cheap and touches no disk.
            model = build_foundation("depth-anything-v2-small")
            with pytest.raises(ModelNotInstalledError):
                model.predict(Image.new("RGB", (8, 8)))
        finally:
            get_settings.cache_clear()
            reset_cache()

    def test_the_catalogue_reports_what_a_full_install_would_cost(self) -> None:
        """A sanity bound, so a mis-typed size cannot quietly claim 30 GB or 30 MB."""
        total_gb = sum(spec.approx_size_mb for spec in all_models()) / 1024
        assert 5 < total_gb < 12, f"catalogue total looks wrong: {total_gb:.1f} GB"


class TestLicensingIsStatedPerEntry:
    """Doc 35. Wave 8 cannot redistribute a non-commercial model, and the person deciding
    to download one has to be told *before* the download, not after."""

    def test_every_spec_names_a_licence(self) -> None:
        from app.ml.registry import all_models

        unnamed = [spec.id for spec in all_models() if not spec.licence.strip()]
        assert unnamed == []

    def test_non_commercial_is_explicit_not_inferred(self) -> None:
        """The flag is authoritative; the licence string is prose.

        Deriving it by looking for "NC" in the text is the same defect as reading a head's
        capability off its `task` label — it works until something is worded differently,
        and it fails silently in the permissive direction. This test states the intent so a
        later refactor to substring-matching has to argue with it.
        """
        from app.ml.registry import ModelSpec

        spec = ModelSpec(
            id="x",
            repo_id="r/x",
            kind="backbone",
            family="dinov2",
            gated=False,
            approx_size_mb=1,
            description="d",
            licence="Some Licence That Never Says En Cee",
            non_commercial=True,
        )
        assert spec.non_commercial is True

    def test_permissive_entries_default_to_commercial_use(self) -> None:
        from app.ml.registry import get_model

        spec = get_model("dinov2-small")
        assert spec is not None
        assert spec.licence == "Apache-2.0"
        assert spec.non_commercial is False



class TestTheStarterSet:
    """What a first run downloads (doc 65).

    Reported as "there are no preinstalled models", and there cannot be: this set is ~1.1 GB,
    which is too much for a git clone and several times the whole installer. So the flag does
    not make anything smaller — it makes the choice for someone who has just cloned the repo
    and is looking at fifteen models with no way to tell which five matter.
    """

    def test_it_covers_every_feature_rather_than_every_model(self) -> None:
        """The set is pinned by id on purpose. Adding a sixth is a size decision — a
        gigabyte is already a real one on a tether — and it should not happen by someone
        typing `starter=True` while adding an unrelated model."""
        starter = {spec.id for spec in all_models() if spec.starter}
        assert starter == {
            "dinov2-small",  # the backbone every trained head runs on
            "rf-detr-nano",  # the general detector, and the one to fine-tune
            "grounding-dino-tiny",  # half of Grounded SAM
            "sam2.1-hiera-small",  # the other half
            "depth-anything-v2-small",
        }

    def test_grounded_sam_is_starter_as_a_whole_or_not_at_all(self) -> None:
        """Its two models are useless apart. Marking one and not the other would download
        658 MB and still leave concept segmentation unavailable — which is the confusing
        half-installed state this feature exists to remove."""
        from app.ml.annotators.registry import get_annotator

        grounded = get_annotator("grounded-sam")
        assert grounded is not None
        for model_id in grounded.model_ids:
            spec = get_model(model_id)
            assert spec is not None and spec.starter, f"{model_id} missing from the starter set"

    def test_nothing_gated_is_in_it(self) -> None:
        """One click has to actually work. A gated model needs a HuggingFace token and, for
        SAM 3, an access request approved by hand — so including one turns "download all"
        into a run that stops partway with a 409 nobody was expecting."""
        for spec in all_models():
            if spec.starter:
                assert not spec.gated, f"{spec.id} is gated and cannot be part of one click"
                assert not spec.requires_access_request

    def test_it_is_the_smallest_of_its_family(self) -> None:
        """`-small`/`-nano` throughout: this is the set that makes the app work, not the set
        that makes it good. Someone who wants base or large can see them in the list."""
        for spec in all_models():
            if spec.starter:
                siblings = [other for other in all_models() if other.family == spec.family]
                assert spec.approx_size_mb == min(other.approx_size_mb for other in siblings), (
                    f"{spec.id} is not the smallest {spec.family}"
                )

    def test_the_download_stays_within_what_a_user_will_sit_through(self) -> None:
        """A bound, not a target. The panel quotes this figure before the click, and if a
        catalogue edit doubles it the quote is still honest but the feature is not."""
        megabytes = sum(spec.approx_size_mb for spec in all_models() if spec.starter)
        assert 800 < megabytes < 1500, f"starter set is {megabytes} MB"

    def test_it_is_a_fraction_of_the_full_catalogue(self) -> None:
        # The point of a starter set: ~1.1 GB instead of the ~8 GB everything would cost.
        full = sum(spec.approx_size_mb for spec in all_models())
        starter = sum(spec.approx_size_mb for spec in all_models() if spec.starter)
        assert starter < full / 4

    def test_the_api_reports_the_flag(self) -> None:
        """The UI reads the set from the catalogue rather than holding a list of its own,
        so dropping this field from the DTO silently empties the panel."""
        from fastapi.testclient import TestClient

        from app.main import create_app

        with TestClient(create_app()) as test_client:
            response = test_client.get("/api/v1/models")

        assert response.status_code == 200
        by_id = {entry["id"]: entry for entry in response.json()["models"]}
        assert by_id["dinov2-small"]["starter"] is True
        assert by_id["dinov2-large"]["starter"] is False


class TestTheFrontendKnowsEveryFamily:
    """The catalogue's families cross a language boundary, and the crossing has failed twice.

    `models.ts` mirrors this module by hand and says so in a comment: "grep this file
    whenever a backend literal changes". That instruction has been missed twice — `segmenter`
    arrived with Wave 4 and was never added, and `rf-detr` was added with a full set of cards,
    licences and a working download route that **no screen ever rendered**, because the Admin
    tab's family list did not mention it. Both failures are silent in both languages: Python
    does not read TypeScript, and TypeScript never assigned the missing literal, so there was
    nothing to fail.

    So the grep is a test now. It is a string search rather than a parse on purpose — the
    question is only "does this literal appear in the union", and a parser here would be a
    second thing to maintain for no extra answer.
    """

    def _models_ts(self) -> str:
        import pathlib

        path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "apps"
            / "frontend"
            / "src"
            / "api"
            / "models.ts"
        )
        assert path.exists(), f"the frontend contract moved: {path}"
        return path.read_text(encoding="utf-8")

    def test_every_family_is_in_the_typescript_union(self) -> None:
        source = self._models_ts()
        missing = [
            spec.family for spec in all_models() if f"'{spec.family}'" not in source
        ]
        assert missing == [], f"models.ts has no ModelFamily entry for: {sorted(set(missing))}"

    def test_every_family_has_a_label_to_render_under(self) -> None:
        """A family in the type with no label is a compile error; a family with a label is
        rendered, because the order is derived from the labels. This pins the second half —
        that the label map is what the section list is built from, which is the fix for a
        hand-maintained order array that silently omitted two families."""
        source = self._models_ts()
        labels = source.split("FAMILY_LABELS", 1)[1].split("});", 1)[0]
        missing = [spec.family for spec in all_models() if spec.family not in labels]
        assert missing == [], f"no FAMILY_LABELS entry for: {sorted(set(missing))}"

    def test_every_kind_is_in_the_typescript_union(self) -> None:
        """The same crossing, for `ModelKind` — the literal that drifted the first time."""
        source = self._models_ts()
        missing = [spec.kind for spec in all_models() if f"'{spec.kind}'" not in source]
        assert missing == [], f"models.ts has no ModelKind entry for: {sorted(set(missing))}"
