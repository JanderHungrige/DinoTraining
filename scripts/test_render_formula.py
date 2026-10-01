"""Tests for scripts/render_formula.py (doc 130)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_formula

SHA = "a" * 64


def test_the_release_url_and_checksum_are_filled_in() -> None:
    formula = render_formula.render("0.2.0", SHA)
    assert (
        'url "https://github.com/JanderHungrige/DinoTraining/releases/download/'
        'v0.2.0/DinoTraining_0.2.0_aarch64.app.tar.gz"'
    ) in formula
    assert f'sha256 "{SHA}"' in formula
    assert "{{" not in formula


def test_a_tag_with_v_is_accepted() -> None:
    assert "/v0.2.0/" in render_formula.render("v0.2.0", SHA)


def test_it_is_a_formula_not_a_cask() -> None:
    # A cask would quarantine the download, and the unsigned app would be blocked.
    formula = render_formula.render("0.2.0", SHA)
    assert "class Dinotraining < Formula" in formula
    assert "depends_on arch: :arm64" in formula


@pytest.mark.parametrize(
    ("version", "sha"),
    [("latest", SHA), ("0.2", SHA), ("0.2.0", "abc"), ("0.2.0", "A" * 64)],
)
def test_bad_input_is_refused(version: str, sha: str) -> None:
    with pytest.raises(SystemExit):
        render_formula.render(version, sha)


def test_an_unknown_placeholder_is_refused() -> None:
    with pytest.raises(SystemExit, match="placeholder"):
        render_formula.render("0.2.0", SHA, template="{{version}} {{other}}")
