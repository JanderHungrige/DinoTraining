"""Tests for download progress accounting.

Regression cover for a real bug: summing per-bar *deltas* against a single bar's
total made a finished download report 194%.
"""

from __future__ import annotations

import io

from app.ml.downloads import DownloadJob, _make_tqdm_class


def make_job() -> DownloadJob:
    return DownloadJob(job_id="j", model_id="dinov2-small")


class TestProgressAccounting:
    def test_single_bar_reports_its_position(self) -> None:
        job = make_job()
        job.report_bar(1, 50, 100)
        assert (job.downloaded_bytes, job.total_bytes) == (50, 100)

    def test_repeat_reports_replace_rather_than_accumulate(self) -> None:
        """Bars report absolute positions; treating them as deltas double-counts."""
        job = make_job()
        job.report_bar(1, 30, 100)
        job.report_bar(1, 60, 100)
        job.report_bar(1, 90, 100)
        assert job.downloaded_bytes == 90

    def test_concurrent_bars_sum_both_sides(self) -> None:
        job = make_job()
        job.report_bar(1, 40, 100)
        job.report_bar(2, 25, 50)
        assert (job.downloaded_bytes, job.total_bytes) == (65, 150)

    def test_progress_never_exceeds_the_total(self) -> None:
        """The original defect: 328 MB downloaded against a 168 MB total."""
        job = make_job()
        for bar, (current, total) in enumerate([(100, 100), (68, 68), (160, 160)]):
            job.report_bar(bar, current, total)
        assert job.downloaded_bytes <= job.total_bytes

    def test_completion_pins_progress_to_the_total(self) -> None:
        job = make_job()
        job.report_bar(1, 97, 100)
        job.finish("complete")
        assert job.downloaded_bytes == job.total_bytes

    def test_failure_does_not_fake_full_progress(self) -> None:
        job = make_job()
        job.report_bar(1, 12, 100)
        job.finish("failed", "boom")
        assert job.downloaded_bytes == 12
        assert job.message == "boom"


class TestJobTqdm:
    def test_byte_bars_are_tracked(self) -> None:
        job = make_job()
        tqdm_class = _make_tqdm_class(job)
        bar = tqdm_class(total=100, unit="B", file=io.StringIO())
        bar.update(40)
        assert job.downloaded_bytes == 40
        bar.close()

    def test_file_count_bars_are_ignored(self) -> None:
        """The 'Fetching N files' bar counts files; mixing it in corrupts the total."""
        job = make_job()
        tqdm_class = _make_tqdm_class(job)
        bar = tqdm_class(total=3, file=io.StringIO())
        bar.update(1)
        assert job.downloaded_bytes == 0
        assert job.total_bytes == 0
        bar.close()

    def test_two_file_bars_aggregate_correctly(self) -> None:
        job = make_job()
        tqdm_class = _make_tqdm_class(job)
        first = tqdm_class(total=100, unit="B", file=io.StringIO())
        second = tqdm_class(total=200, unit="B", file=io.StringIO())

        first.update(100)
        second.update(50)

        assert job.total_bytes == 300
        assert job.downloaded_bytes == 150
        first.close()
        second.close()

    def test_close_captures_a_bar_that_never_updated(self) -> None:
        job = make_job()
        tqdm_class = _make_tqdm_class(job)
        bar = tqdm_class(total=64, unit="B", file=io.StringIO())
        bar.n = 64
        bar.close()
        assert job.downloaded_bytes == 64
