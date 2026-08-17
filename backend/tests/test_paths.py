"""Tests for app.core.paths — confinement is the security primitive here."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.paths import (
    PathConfinementError,
    directory_size_bytes,
    ensure_within,
    is_installed,
    model_cache_root,
    resolve_model_dir,
)


class TestEnsureWithin:
    def test_allows_a_direct_child(self, tmp_path: Path) -> None:
        assert ensure_within(tmp_path, tmp_path / "dinov2-base") == (
            tmp_path / "dinov2-base"
        ).resolve()

    def test_allows_a_nested_descendant(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c"
        assert ensure_within(tmp_path, target) == target.resolve()

    def test_allows_the_root_itself(self, tmp_path: Path) -> None:
        assert ensure_within(tmp_path, tmp_path) == tmp_path.resolve()

    def test_rejects_parent_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(PathConfinementError):
            ensure_within(tmp_path, tmp_path / ".." / "elsewhere")

    def test_rejects_deep_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(PathConfinementError):
            ensure_within(tmp_path, tmp_path / "a" / ".." / ".." / ".." / "etc" / "passwd")

    def test_rejects_an_unrelated_absolute_path(self, tmp_path: Path) -> None:
        with pytest.raises(PathConfinementError):
            ensure_within(tmp_path, Path("/etc"))

    def test_rejects_a_symlink_pointing_outside(self, tmp_path: Path) -> None:
        """Resolution happens before comparison, so a symlink cannot smuggle a path out."""
        outside = tmp_path.parent / "outside-target"
        outside.mkdir(exist_ok=True)
        root = tmp_path / "root"
        root.mkdir()
        (root / "escape").symlink_to(outside, target_is_directory=True)

        with pytest.raises(PathConfinementError):
            ensure_within(root, root / "escape")

    def test_rejects_a_sibling_with_a_shared_prefix(self, tmp_path: Path) -> None:
        """`/cache-evil` must not pass a check against `/cache`."""
        root = tmp_path / "cache"
        root.mkdir()
        sibling = tmp_path / "cache-evil"
        sibling.mkdir()

        with pytest.raises(PathConfinementError):
            ensure_within(root, sibling)


class TestResolveModelDir:
    def test_is_inside_the_cache_root(self, tmp_path: Path) -> None:
        settings = Settings(_env_file=None, model_cache_dir=tmp_path)
        directory = resolve_model_dir("dinov2-base", settings)
        assert directory.parent == model_cache_root(settings)

    def test_traversal_in_the_id_is_refused(self, tmp_path: Path) -> None:
        settings = Settings(_env_file=None, model_cache_dir=tmp_path)
        with pytest.raises(PathConfinementError):
            resolve_model_dir("../../etc", settings)

    def test_honours_the_configured_cache_dir(self, tmp_path: Path) -> None:
        settings = Settings(_env_file=None, model_cache_dir=tmp_path / "weights")
        assert resolve_model_dir("dinov2-small", settings) == (
            tmp_path / "weights" / "dinov2-small"
        ).resolve()


class TestDirectoryInspection:
    def test_size_of_a_missing_directory_is_zero(self, tmp_path: Path) -> None:
        assert directory_size_bytes(tmp_path / "nope") == 0

    def test_size_sums_nested_files(self, tmp_path: Path) -> None:
        (tmp_path / "nested").mkdir()
        (tmp_path / "a.bin").write_bytes(b"x" * 100)
        (tmp_path / "nested" / "b.bin").write_bytes(b"y" * 50)
        assert directory_size_bytes(tmp_path) == 150

    def test_size_ignores_symlinks(self, tmp_path: Path) -> None:
        """An HF cache is full of symlinks into blobs; following them double-counts."""
        (tmp_path / "real.bin").write_bytes(b"z" * 40)
        (tmp_path / "link.bin").symlink_to(tmp_path / "real.bin")
        assert directory_size_bytes(tmp_path) == 40

    def test_empty_directory_is_not_installed(self, tmp_path: Path) -> None:
        assert is_installed(tmp_path) is False

    def test_missing_directory_is_not_installed(self, tmp_path: Path) -> None:
        assert is_installed(tmp_path / "absent") is False

    def test_directory_with_content_is_installed(self, tmp_path: Path) -> None:
        (tmp_path / "config.json").write_text("{}")
        assert is_installed(tmp_path) is True
