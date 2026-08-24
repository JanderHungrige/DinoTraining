"""The foundation-model contract (doc 36).

These tests are about *shape and dispatch*, not about depth quality — the real model is
exercised in Phase 7b against real weights. What matters here is that a self-contained
model produces something the viewer cannot distinguish from a head's prediction, and that
adding the next one stays a catalogue entry plus one case in `build_foundation`.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.foundation.build import (
    FoundationUnavailableError,
    build_foundation,
    reset_cache,
)
from app.ml.foundation.depth import DepthAnythingModel
from app.ml.foundation.registry import all_foundations, get_foundation
from app.ml.inference.payloads import encode_depth_map
from app.ml.registry import get_model


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    reset_cache()


class TestTheRegistry:
    def test_ids_are_unique(self) -> None:
        ids = [spec.id for spec in all_foundations()]
        assert len(ids) == len(set(ids))

    def test_every_spec_names_a_model_the_catalogue_has(self) -> None:
        """A foundation spec pointing at a missing catalogue entry would list a model that
        can never be installed — visible in the picker, impossible to run."""
        for spec in all_foundations():
            assert get_model(spec.model_id) is not None, spec.id

    def test_every_spec_declares_a_render_hint(self) -> None:
        """`render_hint` is what the overlay registry dispatches on. Without it the
        prediction arrives and nothing knows how to draw it."""
        for spec in all_foundations():
            assert spec.render_hint in {"labels", "boxes", "masks", "depth-map"}

    def test_unknown_id_returns_none(self) -> None:
        assert get_foundation("does-not-exist") is None


class TestBuildIsTheOnlyDispatch:
    def test_it_builds_a_known_model(self) -> None:
        assert isinstance(build_foundation("depth-anything-v2-small"), DepthAnythingModel)

    def test_it_refuses_an_unknown_id(self) -> None:
        with pytest.raises(FoundationUnavailableError):
            build_foundation("not-a-model")

    def test_a_traversal_id_is_refused_by_the_registry_lookup(self) -> None:
        # Same guarantee doc 02 gives the model catalogue: a caller names a key, never a
        # path or a repo, so traversal fails at the lookup rather than at the filesystem.
        with pytest.raises(FoundationUnavailableError):
            build_foundation("../../etc/passwd")

    def test_the_same_id_returns_the_same_instance(self) -> None:
        """Weights cost seconds to load and the viewer runs one model over a whole folder."""
        first = build_foundation("depth-anything-v2-small")
        assert build_foundation("depth-anything-v2-small") is first

    def test_reset_drops_the_cache(self) -> None:
        first = build_foundation("depth-anything-v2-small")
        reset_cache()
        assert build_foundation("depth-anything-v2-small") is not first

    def test_no_module_outside_build_maps_an_id_to_an_implementation(self) -> None:
        """The rule Wave 4 set for annotators, applied here.

        An `if foundation_id == "…"` elsewhere is what turns "add an entry and one case"
        into "grep the codebase", which is exactly what the mask-annotator registry was
        built to avoid.
        """
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[1] / "app"
        offenders = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*.py")
            if "DepthAnythingModel(" in path.read_text(encoding="utf-8")
            and path.name not in {"build.py", "depth.py"}
        ]
        assert offenders == [], f"implementation constructed outside build.py: {offenders}"


class TestTheDepthPayloadIsIndistinguishable:
    """A foundation model's depth map and a trained head's must encode identically.

    They reach the renderer through different paths — the head goes through letterbox
    geometry, the foundation model through its own processor — and the overlay must not be
    able to tell. That is the whole reason `encode_depth_map` was split out.
    """

    def test_it_carries_the_keys_the_renderer_reads(self) -> None:
        payload = encode_depth_map(torch.rand(20, 30))
        assert set(payload) == {"depth_png", "min", "max", "height", "width"}

    def test_dimensions_are_the_tensors_own(self) -> None:
        payload = encode_depth_map(torch.rand(20, 30))
        assert (payload["height"], payload["width"]) == (20, 30)

    def test_min_and_max_carry_the_real_range(self) -> None:
        # The PNG is a *display* encoding; min/max are what map a pixel back to metres.
        depth = torch.tensor([[1.5, 2.5], [3.5, 4.5]])
        payload = encode_depth_map(depth)
        assert payload["min"] == pytest.approx(1.5)
        assert payload["max"] == pytest.approx(4.5)

    def test_a_flat_depth_map_does_not_divide_by_zero(self) -> None:
        """Every pixel equal is a real case — a blank wall, or a failed prediction."""
        payload = encode_depth_map(torch.full((4, 4), 2.0))
        assert payload["min"] == pytest.approx(2.0)
        assert payload["max"] == pytest.approx(2.0)
        assert isinstance(payload["depth_png"], str)

    def test_it_accepts_a_tensor_that_is_not_a_plain_cpu_leaf(self) -> None:
        """Wave 3's bug: `.numpy()` raises on anything with a device or a graph, and every
        unit test builds plain CPU tensors. A `requires_grad` tensor fails in the same
        place for the same reason and runs everywhere."""
        depth = torch.rand(6, 6, requires_grad=True) * 2
        payload = encode_depth_map(depth)
        assert payload["height"] == 6
