"""The written dataset-format guide, checked against the importer it describes (doc 48).

The Head Trainer shows the user prose explaining what a dataset must look like, so they can
download one from anywhere and save it correctly. **Prose that quietly stops being true is
worse than no prose** — the panel renders whatever string it holds, and no frontend test can
tell whether the claim still matches `coco_import.py`.

So these read the frontend's own constants. Renaming the annotation file, or making the
search recursive, fails here rather than misleading someone six months later.

Split from `test_coco_import.py` for the 300-line rule; the seam is that everything there
tests the importer and everything here tests what the app *says* about it.
"""

from __future__ import annotations

from pathlib import Path

from app.datasets.coco_import import COCO_FILENAME, find_coco_files

GUIDE = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "frontend"
    / "src"
    / "tabs"
    / "datasetFormat.ts"
)


def _guide_text() -> str:
    assert GUIDE.is_file(), f"doc 48's content moved from {GUIDE}; update this test with it"
    return GUIDE.read_text(encoding="utf-8")


class TestTheGuideMatchesTheImporter:
    def test_it_names_this_annotation_filename(self) -> None:
        assert f"'{COCO_FILENAME}'" in _guide_text()

    def test_it_still_claims_a_one_level_search(self) -> None:
        assert "SEARCH_DEPTH = 1" in _guide_text()

    def test_the_search_really_is_one_level(self, tmp_path: Path) -> None:
        """The claim, pinned against the function rather than against its comment."""
        nested = tmp_path / "splits" / "train"
        nested.mkdir(parents=True)
        (nested / COCO_FILENAME).write_text("{}")
        assert find_coco_files(tmp_path) == []

        shallow = tmp_path / "train"
        shallow.mkdir()
        (shallow / COCO_FILENAME).write_text("{}")
        assert find_coco_files(tmp_path) == [shallow / COCO_FILENAME]

    def test_it_warns_against_the_category_zero_trap(self) -> None:
        # The bug doc 31 actually hit: two reference datasets have a placeholder at id 0,
        # and the third's id 0 is the real class `platelets`.
        assert "platelets" in _guide_text()

    def test_it_gives_the_box_convention_and_what_it_is_not(self) -> None:
        text = _guide_text()
        assert "absolute pixels from the top-left" in text
        assert "x1, y1, x2, y2" in text
