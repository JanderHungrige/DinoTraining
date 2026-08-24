"""Training some of the backbone (doc 55).

Everything here guards one failure mode: **a run that reports unfreezing and trains only
the head.** It completes, the losses look plausible, and the number it produces is the
frozen number — which is indistinguishable from "unfreezing did not help".
"""

from __future__ import annotations

import pytest
import torch
from torch import nn

from app.ml.backbone import load_backbone
from app.ml.training.config import TrainingConfig
from app.ml.training.unfreeze import (
    ALL_BLOCKS,
    BackboneNotUnfreezableError,
    apply_unfreeze,
    blocks_of,
    caching_is_valid,
    optimiser_for,
)


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    return load_backbone("dinov2-small")


class TestTheCacheGate:
    """The single most important rule in the module.

    Cached features are computed once, before training. If the backbone trains too they are
    stale from epoch two — and worse, the backbone is not in the graph at all, so it
    receives no gradients while the job reports millions of trainable parameters.
    """

    def test_a_frozen_run_may_cache(self) -> None:
        assert caching_is_valid(0) is True

    def test_any_unfreezing_forbids_the_cache(self) -> None:
        assert caching_is_valid(1) is False
        assert caching_is_valid(6) is False
        assert caching_is_valid(ALL_BLOCKS) is False


class TestWhatGetsUnfrozen:
    def test_zero_leaves_everything_frozen(self, backbone) -> None:  # type: ignore[no-untyped-def]
        frozen, trainable = apply_unfreeze(backbone, 0)
        assert trainable == 0
        assert frozen > 20_000_000

    def test_it_reports_the_split_rather_than_only_logging_it(self, backbone) -> None:  # type: ignore[no-untyped-def]
        frozen, trainable = apply_unfreeze(backbone, 2)
        assert trainable > 0
        assert frozen > trainable, "two of twelve blocks should be the minority"

    def test_more_blocks_means_more_trainable(self, backbone) -> None:  # type: ignore[no-untyped-def]
        _, two = apply_unfreeze(backbone, 2)
        _, six = apply_unfreeze(backbone, 6)
        assert six > two

    def test_it_unfreezes_the_last_blocks_not_the_first(self, backbone) -> None:  # type: ignore[no-untyped-def]
        """A ViT's later blocks carry the task-specific representation; the early ones carry
        general structure a few hundred images cannot improve and can easily damage."""
        apply_unfreeze(backbone, 1)
        layers = blocks_of(backbone)
        assert all(not p.requires_grad for p in layers[0].parameters())
        assert all(p.requires_grad for p in layers[-1].parameters())

    def test_all_includes_the_embeddings_not_only_the_blocks(self, backbone) -> None:  # type: ignore[no-untyped-def]
        # "All" that quietly meant "all the blocks" would leave the patch embedding frozen
        # and nothing would say so.
        _, trainable = apply_unfreeze(backbone, ALL_BLOCKS)
        total = sum(int(p.numel()) for p in backbone.model.parameters())
        assert trainable == total

    def test_asking_for_more_blocks_than_exist_is_clamped(self, backbone) -> None:
        _, many = apply_unfreeze(backbone, 999)
        _, every = apply_unfreeze(backbone, ALL_BLOCKS)
        # Clamped to the block count, so it is everything *in the blocks* but not the
        # embeddings — which is why it is not equal to ALL.
        assert 0 < many <= every

    def test_it_resets_between_calls(self, backbone) -> None:  # type: ignore[no-untyped-def]
        """A backbone left trainable by a previous run in the same process would silently
        train in the next one. The runner calls this even on the frozen path for that."""
        apply_unfreeze(backbone, ALL_BLOCKS)
        _, trainable = apply_unfreeze(backbone, 0)
        assert trainable == 0

    def test_an_unaddressable_backbone_raises_rather_than_training_nothing(self) -> None:
        class Odd:
            model = nn.Linear(2, 2)
            device = "cpu"

        with pytest.raises(BackboneNotUnfreezableError, match="frozen"):
            blocks_of(Odd())  # type: ignore[arg-type]


class TestTheOptimiser:
    def test_a_frozen_backbone_contributes_no_group(self, backbone) -> None:  # type: ignore[no-untyped-def]
        # An empty param group makes AdamW raise, and the frozen path is legitimate.
        apply_unfreeze(backbone, 0)
        head = nn.Linear(4, 2)
        assert len(optimiser_for(head, backbone, 1e-3, 0.01).param_groups) == 1

    def test_an_unfrozen_backbone_gets_its_own_group(self, backbone) -> None:  # type: ignore[no-untyped-def]
        apply_unfreeze(backbone, 2)
        head = nn.Linear(4, 2)
        assert len(optimiser_for(head, backbone, 1e-3, 0.01).param_groups) == 2

    def test_the_backbone_trains_slower_than_the_head(self, backbone) -> None:  # type: ignore[no-untyped-def]
        """One shared rate is the setting that makes unfreezing look like a bad idea: at
        1e-3 a pretrained ViT is destroyed by the first few hundred images."""
        apply_unfreeze(backbone, 2)
        groups = optimiser_for(head=nn.Linear(4, 2), backbone=backbone, learning_rate=1e-3,
                               weight_decay=0.01, backbone_lr_scale=0.1).param_groups
        assert groups[0]["lr"] == pytest.approx(1e-3)
        assert groups[1]["lr"] == pytest.approx(1e-4)

    def test_only_unfrozen_parameters_are_handed_to_the_optimiser(self, backbone) -> None:  # type: ignore[no-untyped-def]
        apply_unfreeze(backbone, 1)
        groups = optimiser_for(nn.Linear(4, 2), backbone, 1e-3, 0.01).param_groups
        assert all(bool(p.requires_grad) for p in groups[1]["params"])


class TestTheConfig:
    def test_it_defaults_to_the_founding_rule(self) -> None:
        config = TrainingConfig(head_type_id="h", backbone_id="b", dataset_ids=("d",))
        assert config.unfreeze_blocks == 0
        assert caching_is_valid(config.unfreeze_blocks) is True

    def test_unfreezing_a_head_is_refused_outright(self) -> None:
        """Measured on 2026-08-21: a head trained against an unfrozen backbone scored
        **0.000 mAP** in a fresh process. A `HeadInstance` stores head weights plus a
        `backbone_id` — there is nowhere to put a modified backbone, so the weights the
        head was fitted against are discarded and the head predicts nothing, after a run
        that reported a plausible validation number."""
        with pytest.raises(ValueError, match="not supported for heads"):
            TrainingConfig(
                head_type_id="h", backbone_id="b", dataset_ids=("d",), unfreeze_blocks=4
            )

    def test_the_refusal_says_where_to_go_instead(self) -> None:
        with pytest.raises(ValueError, match="[Ff]ine-tun"):
            TrainingConfig(
                head_type_id="h", backbone_id="b", dataset_ids=("d",), unfreeze_blocks=-1
            )

    def test_a_backbone_rate_above_the_head_is_refused(self) -> None:
        # Scaling *up* is never what is wanted here and is almost certainly a typo.
        with pytest.raises(ValueError, match="backbone_lr_scale"):
            TrainingConfig(
                head_type_id="h", backbone_id="b", dataset_ids=("d",), backbone_lr_scale=10.0
            )

    def test_a_zero_backbone_rate_is_refused(self) -> None:
        # It would train nothing while reporting the backbone as trainable.
        with pytest.raises(ValueError, match="backbone_lr_scale"):
            TrainingConfig(
                head_type_id="h", backbone_id="b", dataset_ids=("d",), backbone_lr_scale=0.0
            )


class TestGradientsActuallyReachTheBackbone:
    def test_a_trainable_forward_carries_a_graph(self, backbone) -> None:  # type: ignore[no-untyped-def]
        """The decisive check. `extract` wraps its forward in `no_grad`, so a training loop
        that called it would produce features with no `grad_fn` — and the backward pass
        would reach the head and stop, silently."""
        from app.ml.backbone import extract, extract_trainable

        apply_unfreeze(backbone, 1)
        pixels = torch.randn(1, 3, 224, 224)

        assert extract(backbone, pixels).patches.grad_fn is None
        assert extract_trainable(backbone, pixels).patches.grad_fn is not None

    def test_a_step_changes_backbone_weights(self, backbone) -> None:  # type: ignore[no-untyped-def]
        from app.ml.backbone import extract_trainable

        apply_unfreeze(backbone, 1)
        layers = blocks_of(backbone)
        watched = next(p for p in layers[-1].parameters() if p.requires_grad)
        before = watched.detach().clone()

        head = nn.Linear(backbone.capabilities.embed_dim, 1).to(backbone.device)
        optimiser = optimiser_for(head, backbone, 1e-2, 0.0)
        features = extract_trainable(backbone, torch.randn(1, 3, 224, 224))
        loss = head(features.cls).sum()
        optimiser.zero_grad()
        loss.backward()
        optimiser.step()

        assert not torch.allclose(before, watched.detach()), "the backbone did not move"

    def test_a_frozen_block_does_not_move(self, backbone) -> None:  # type: ignore[no-untyped-def]
        from app.ml.backbone import extract_trainable

        apply_unfreeze(backbone, 1)
        layers = blocks_of(backbone)
        frozen = next(iter(layers[0].parameters()))
        before = frozen.detach().clone()

        head = nn.Linear(backbone.capabilities.embed_dim, 1).to(backbone.device)
        optimiser = optimiser_for(head, backbone, 1e-2, 0.0)
        features = extract_trainable(backbone, torch.randn(1, 3, 224, 224))
        loss = head(features.cls).sum()
        optimiser.zero_grad()
        loss.backward()
        optimiser.step()

        assert torch.allclose(before, frozen.detach())
