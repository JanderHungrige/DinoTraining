"""Tests for fetching, verifying and converting first-party head weights.

The ordering assertion — digest checked *before* the pickle is read — is the entire
safety argument for reading a `.pth` at all. If that ever inverts, the carve-out
documented in doc 15 is gone, so it is asserted directly rather than by inspection.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import torch

from app.ml.backbone import BackboneCapabilities
from app.ml.heads.convert import (
    DigestMismatchError,
    UnsupportedCheckpointError,
    load_verified_state_dict,
    remap_state_dict,
    verify_digest,
)
from app.ml.heads.pretrained import (
    ADE20K_CLASSES,
    DEPTH_BINS,
    IMAGENET_CLASSES,
    PretrainedClassifier,
    PretrainedDepth,
    PretrainedSegmenter,
)

EMBED = 8


def capabilities(embed_dim: int = EMBED) -> BackboneCapabilities:
    return BackboneCapabilities(
        model_id="dinov2-small",
        family="dinov2",
        patch_size=14,
        embed_dim=embed_dim,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )


def upstream_classifier(embed_dim: int = EMBED) -> dict[str, torch.Tensor]:
    """Exactly the keys and shapes in dinov2_<m>_linear_head.pth."""
    return {
        "weight": torch.randn(IMAGENET_CLASSES, embed_dim * 2),
        "bias": torch.randn(IMAGENET_CLASSES),
    }


def upstream_segmenter(embed_dim: int = EMBED) -> dict[str, torch.Tensor]:
    """Exactly the keys and shapes in dinov2_<m>_ade20k_linear_head.pth."""
    return {
        "decode_head.conv_seg.weight": torch.randn(ADE20K_CLASSES, embed_dim, 1, 1),
        "decode_head.conv_seg.bias": torch.randn(ADE20K_CLASSES),
        "decode_head.bn.weight": torch.randn(embed_dim),
        "decode_head.bn.bias": torch.randn(embed_dim),
        "decode_head.bn.running_mean": torch.randn(embed_dim),
        "decode_head.bn.running_var": torch.rand(embed_dim) + 1.0,
        "decode_head.bn.num_batches_tracked": torch.tensor(0),
    }


def upstream_depth(embed_dim: int = EMBED) -> dict[str, torch.Tensor]:
    """Exactly the keys and shapes in dinov2_<m>_nyu_linear_head.pth."""
    return {
        "decode_head.conv_depth.weight": torch.randn(DEPTH_BINS, embed_dim * 2, 1, 1),
        "decode_head.conv_depth.bias": torch.randn(DEPTH_BINS),
    }


class TestVerifyDigest:
    def test_matching_digest_passes(self, tmp_path: Path) -> None:
        path = tmp_path / "weights.pth"
        path.write_bytes(b"some weights")
        verify_digest(path, hashlib.sha256(b"some weights").hexdigest())

    def test_mismatched_digest_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "weights.pth"
        path.write_bytes(b"tampered")
        with pytest.raises(DigestMismatchError):
            verify_digest(path, "0" * 64)

    def test_digest_comparison_is_case_insensitive(self, tmp_path: Path) -> None:
        path = tmp_path / "weights.pth"
        path.write_bytes(b"some weights")
        verify_digest(path, hashlib.sha256(b"some weights").hexdigest().upper())

    def test_error_names_both_digests(self, tmp_path: Path) -> None:
        """A digest failure must be diagnosable — a bare 'mismatch' is unactionable."""
        path = tmp_path / "weights.pth"
        path.write_bytes(b"tampered")
        with pytest.raises(DigestMismatchError) as caught:
            verify_digest(path, "a" * 64)
        message = str(caught.value)
        assert "a" * 64 in message
        assert hashlib.sha256(b"tampered").hexdigest() in message


class TestLoadVerifiedStateDict:
    def test_digest_is_checked_before_the_pickle_is_read(self, tmp_path: Path) -> None:
        """The ordering that makes reading a pickle defensible at all.

        The file is deliberately not a valid checkpoint. If the digest were checked
        after the load, torch would raise its own unpickling error first — so
        DigestMismatchError is the proof that verification came first.
        """
        path = tmp_path / "weights.pth"
        path.write_bytes(b"this is not a torch checkpoint at all")
        with pytest.raises(DigestMismatchError):
            load_verified_state_dict(path, "b" * 64)

    def test_loads_a_verified_checkpoint(self, tmp_path: Path) -> None:
        path = tmp_path / "weights.pth"
        torch.save(upstream_classifier(), path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()

        loaded = load_verified_state_dict(path, digest)
        assert set(loaded) == {"weight", "bias"}

    def test_unwraps_a_state_dict_wrapper(self, tmp_path: Path) -> None:
        """Some upstream checkpoints nest under 'state_dict'; both shapes must work."""
        path = tmp_path / "weights.pth"
        torch.save({"state_dict": upstream_segmenter()}, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()

        loaded = load_verified_state_dict(path, digest)
        assert "decode_head.conv_seg.weight" in loaded

    def test_rejects_a_checkpoint_that_is_not_a_mapping(self, tmp_path: Path) -> None:
        path = tmp_path / "weights.pth"
        torch.save(torch.randn(4), path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()

        with pytest.raises(UnsupportedCheckpointError):
            load_verified_state_dict(path, digest)


class TestRemap:
    """Remapped keys must exactly equal the target module's, then load strict=True."""

    def test_classifier_keys(self) -> None:
        remapped = remap_state_dict("dinov2-linear-classifier-in1k", upstream_classifier())
        assert set(remapped) == {"linear.weight", "linear.bias"}

    def test_segmenter_keys(self) -> None:
        remapped = remap_state_dict("dinov2-linear-segmenter-ade20k", upstream_segmenter())
        assert set(remapped) == set(PretrainedSegmenter(embed_dim=EMBED).state_dict())

    def test_depth_keys(self) -> None:
        remapped = remap_state_dict("dinov2-linear-depth-nyu", upstream_depth())
        assert set(remapped) == {"conv_depth.weight", "conv_depth.bias"}

    def test_classifier_loads_strictly(self) -> None:
        head = PretrainedClassifier(embed_dim=EMBED)
        remapped = remap_state_dict("dinov2-linear-classifier-in1k", upstream_classifier())
        head.load_state_dict(remapped, strict=True)

    def test_segmenter_loads_strictly(self) -> None:
        head = PretrainedSegmenter(embed_dim=EMBED)
        remapped = remap_state_dict("dinov2-linear-segmenter-ade20k", upstream_segmenter())
        head.load_state_dict(remapped, strict=True)

    def test_depth_loads_strictly(self) -> None:
        head = PretrainedDepth(embed_dim=EMBED)
        remapped = remap_state_dict("dinov2-linear-depth-nyu", upstream_depth())
        head.load_state_dict(remapped, strict=True)

    def test_values_survive_the_remap(self) -> None:
        """Renaming must not transpose, clone-detach or otherwise disturb the tensors."""
        raw = upstream_classifier()
        remapped = remap_state_dict("dinov2-linear-classifier-in1k", raw)
        assert torch.equal(remapped["linear.weight"], raw["weight"])
        assert torch.equal(remapped["linear.bias"], raw["bias"])

    def test_unknown_head_type_raises(self) -> None:
        with pytest.raises(LookupError):
            remap_state_dict("not-a-head-type", upstream_classifier())

    def test_unexpected_keys_are_rejected(self) -> None:
        """Silently dropping a key would mean loading a partly-initialised head."""
        raw = upstream_depth()
        raw["decode_head.surprise"] = torch.randn(4)
        with pytest.raises(UnsupportedCheckpointError):
            remap_state_dict("dinov2-linear-depth-nyu", raw)

    def test_missing_keys_are_rejected(self) -> None:
        raw = upstream_depth()
        del raw["decode_head.conv_depth.bias"]
        with pytest.raises(UnsupportedCheckpointError):
            remap_state_dict("dinov2-linear-depth-nyu", raw)


class TestEndToEndConversion:
    def test_a_converted_head_produces_finite_output(self, tmp_path: Path) -> None:
        """The point of the whole path: a real forward pass after conversion."""
        from app.ml.backbone import BackboneFeatures

        path = tmp_path / "weights.pth"
        torch.save(upstream_depth(), path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()

        raw = load_verified_state_dict(path, digest)
        remapped = remap_state_dict("dinov2-linear-depth-nyu", raw)

        head = PretrainedDepth(embed_dim=EMBED)
        head.load_state_dict(remapped, strict=True)
        head.eval()

        with torch.no_grad():
            out = head(
                BackboneFeatures(
                    cls=torch.randn(1, EMBED),
                    patches=torch.randn(1, EMBED, 3, 4),
                    grid=(3, 4),
                )
            )
        assert torch.isfinite(out["depth"]).all()
        assert (out["depth"] > 0).all()
