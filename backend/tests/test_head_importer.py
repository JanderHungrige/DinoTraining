"""Tests for community head import — the untrusted half of doc 15.

``repo_id`` is the only fully attacker-controlled string in this feature, and the
safetensors rule is the only thing standing between a stranger's repo and
``torch.load``. Both are tested for what they *refuse*, not just what they accept.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import torch
from safetensors.torch import save_file

from app.core.config import Settings
from app.ml.errors import ModelNotInstalledError
from app.ml.heads.importer import (
    InvalidRepoIdError,
    PickleRefusedError,
    import_community_head,
    validate_repo_id,
)
from app.ml.heads.register import IncompatibleHeadError
from app.ml.heads.store import HeadInstanceStore
from tests.head_testkit import install_fake_backbone


def write_head(path: Path, num_classes: int, embed_dim: int) -> Path:
    save_file(
        {
            "linear.weight": torch.randn(num_classes, embed_dim),
            "linear.bias": torch.randn(num_classes),
        },
        str(path),
    )
    return path


def patch_repo(
    monkeypatch: pytest.MonkeyPatch, files: list[str], local: Path | None = None
) -> None:
    monkeypatch.setattr("app.ml.heads.importer._list_repo_files", lambda repo_id: files)
    if local is not None:
        monkeypatch.setattr(
            "app.ml.heads.importer._download_repo_file",
            lambda repo_id, filename, token: local,
        )


class TestValidateRepoId:
    @pytest.mark.parametrize("repo_id", ["facebook/dinov2-small", "a/b", "Org-1/model_2.x"])
    def test_accepts_owner_slash_name(self, repo_id: str) -> None:
        assert validate_repo_id(repo_id) == repo_id

    @pytest.mark.parametrize(
        "repo_id",
        [
            "../../etc/passwd",
            "owner/../escape",
            "owner/name/extra",
            "https://example.com/owner/name",
            "no-slash",
            "/leading",
            "trailing/",
            "owner/na me",
            "",
            "owner/..",
            "owner/.",
            "../owner/name",
        ],
    )
    def test_rejects_anything_else(self, repo_id: str) -> None:
        with pytest.raises(InvalidRepoIdError):
            validate_repo_id(repo_id)


class TestRefusals:
    def test_pickle_only_repo_is_refused(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """There must be no 'prefer safetensors, fall back to pickle' branch."""
        install_fake_backbone(head_settings, "dinov2-small", 384)
        patch_repo(monkeypatch, ["config.json", "pytorch_model.pth"])

        with pytest.raises(PickleRefusedError) as caught:
            import_community_head(
                repo_id="someone/pickled-head",
                head_type_id="linear-classifier",
                backbone_id="dinov2-small",
                settings=head_settings,
            )
        assert "safetensors" in str(caught.value).lower()

    def test_refusal_names_the_offending_file(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        install_fake_backbone(head_settings, "dinov2-small", 384)
        patch_repo(monkeypatch, ["weights.pt", "other.bin"])

        with pytest.raises(PickleRefusedError) as caught:
            import_community_head(
                repo_id="someone/pickled-head",
                head_type_id="linear-classifier",
                backbone_id="dinov2-small",
                settings=head_settings,
            )
        assert "weights.pt" in str(caught.value)

    def test_backbone_is_checked_before_any_network_call(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def explode(repo_id: str) -> list[str]:
            raise AssertionError("Must not touch the network before checking the backbone")

        monkeypatch.setattr("app.ml.heads.importer._list_repo_files", explode)

        with pytest.raises(ModelNotInstalledError):
            import_community_head(
                repo_id="someone/head",
                head_type_id="linear-classifier",
                backbone_id="dinov2-base",
                settings=head_settings,
            )

    def test_unknown_head_type_is_rejected(self, head_settings: Settings) -> None:
        install_fake_backbone(head_settings, "dinov2-small", 384)
        with pytest.raises(LookupError):
            import_community_head(
                repo_id="someone/head",
                head_type_id="not-a-head-type",
                backbone_id="dinov2-small",
                settings=head_settings,
            )

    def test_incompatible_family_is_explained(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A DINOv2-only head against a DINOv3 backbone must say why, not grey out."""
        install_fake_backbone(head_settings, "dinov3-vitb16", 768)
        patch_repo(monkeypatch, ["model.safetensors"])

        with pytest.raises(IncompatibleHeadError) as caught:
            import_community_head(
                repo_id="someone/head",
                head_type_id="dinov2-linear-segmenter-ade20k",
                backbone_id="dinov3-vitb16",
                settings=head_settings,
            )
        assert "dinov3" in str(caught.value)

    def test_mismatched_tensor_width_is_rejected(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A head built for a 768-wide backbone must not install against a 384-wide one."""
        install_fake_backbone(head_settings, "dinov2-small", 384)
        head_file = write_head(tmp_path / "model.safetensors", num_classes=2, embed_dim=768)
        patch_repo(monkeypatch, ["model.safetensors"], local=head_file)

        with pytest.raises(IncompatibleHeadError):
            import_community_head(
                repo_id="someone/wrong-width",
                head_type_id="linear-classifier",
                backbone_id="dinov2-small",
                num_classes=2,
                settings=head_settings,
            )


class TestClassCountInference:
    """Regression: omitting the class count raised a 500 from build_head.

    A trainable head type requires a count, and the UI's "auto" sends none. The
    weights already encode it, so it is read from them rather than demanded. Found by
    submitting the real form against the running backend — no unit test covered the
    None path because every earlier test passed num_classes explicitly.
    """

    def test_class_count_is_read_from_the_weights_when_omitted(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        install_fake_backbone(head_settings, "dinov2-small", 384)
        head_file = write_head(tmp_path / "model.safetensors", num_classes=7, embed_dim=384)
        patch_repo(monkeypatch, ["model.safetensors"], local=head_file)

        instance = import_community_head(
            repo_id="someone/seven-class",
            head_type_id="linear-classifier",
            backbone_id="dinov2-small",
            settings=head_settings,  # no num_classes — the "auto" path
        )
        assert instance.num_classes == 7

    def test_explicit_count_still_wins(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        install_fake_backbone(head_settings, "dinov2-small", 384)
        head_file = write_head(tmp_path / "model.safetensors", num_classes=4, embed_dim=384)
        patch_repo(monkeypatch, ["model.safetensors"], local=head_file)

        instance = import_community_head(
            repo_id="someone/four-class",
            head_type_id="linear-classifier",
            backbone_id="dinov2-small",
            num_classes=4,
            settings=head_settings,
        )
        assert instance.num_classes == 4

    def test_unreadable_count_asks_the_user_rather_than_crashing(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from safetensors.torch import save_file

        install_fake_backbone(head_settings, "dinov2-small", 384)
        head_file = tmp_path / "model.safetensors"
        # No linear.weight / conv_seg.weight, so the count cannot be inferred.
        save_file({"something.else": torch.randn(3, 384)}, str(head_file))
        patch_repo(monkeypatch, ["model.safetensors"], local=head_file)

        with pytest.raises(IncompatibleHeadError) as caught:
            import_community_head(
                repo_id="someone/opaque",
                head_type_id="linear-classifier",
                backbone_id="dinov2-small",
                settings=head_settings,
            )
        assert "class count" in str(caught.value)


class TestSuccess:
    def test_records_provenance_from_the_bytes_received(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        install_fake_backbone(head_settings, "dinov2-small", 384)
        head_file = write_head(tmp_path / "model.safetensors", num_classes=3, embed_dim=384)
        patch_repo(monkeypatch, ["model.safetensors"], local=head_file)

        instance = import_community_head(
            repo_id="someone/three-class-probe",
            head_type_id="linear-classifier",
            backbone_id="dinov2-small",
            num_classes=3,
            settings=head_settings,
        )

        assert instance.kind == "community"
        assert instance.source_repo == "someone/three-class-probe"
        # Computed from what actually arrived — never a digest the repo claims.
        assert instance.source_digest == hashlib.sha256(head_file.read_bytes()).hexdigest()
        assert instance.embed_dim == 384
        assert instance.num_classes == 3

    def test_imported_head_appears_in_the_picker_list(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        install_fake_backbone(head_settings, "dinov2-small", 384)
        head_file = write_head(tmp_path / "model.safetensors", num_classes=2, embed_dim=384)
        patch_repo(monkeypatch, ["model.safetensors"], local=head_file)

        import_community_head(
            repo_id="someone/probe",
            head_type_id="linear-classifier",
            backbone_id="dinov2-small",
            num_classes=2,
            settings=head_settings,
        )

        listed = HeadInstanceStore(head_settings).list_all(task="classification")
        assert len(listed) == 1
        assert "community" in listed[0].summary
        assert "someone/probe" in listed[0].summary

    def test_weights_are_stored_as_safetensors_not_the_downloaded_file(
        self, head_settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The store owns the on-disk copy; the download cache must not be referenced."""
        install_fake_backbone(head_settings, "dinov2-small", 384)
        head_file = write_head(tmp_path / "model.safetensors", num_classes=2, embed_dim=384)
        patch_repo(monkeypatch, ["model.safetensors"], local=head_file)

        instance = import_community_head(
            repo_id="someone/probe",
            head_type_id="linear-classifier",
            backbone_id="dinov2-small",
            num_classes=2,
            settings=head_settings,
        )

        stored = Path(instance.weights_path)
        assert stored != head_file
        assert stored.suffix == ".safetensors"
        assert stored.is_file()
