"""A video becomes image files a dataset can hold (doc 73).

A real mp4 with identifiable frames, as in doc 68's decode tests: the property worth
proving is that the file named frame 6 *is* frame 6, which a mocked decoder cannot show.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from PIL import Image

from app.ml.video.decode import VideoReadError
from app.ml.video.extract import (
    ExtractConfig,
    FrameExtractor,
    extract_frames,
    frame_filename,
    frames_dir,
)

FRAME_COUNT = 12
STEP = 20


@pytest.fixture(scope="module")
def clip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    import av

    path = tmp_path_factory.mktemp("video") / "run1.mp4"
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=6)
        stream.width, stream.height = 64, 48
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "0", "preset": "ultrafast"}
        for index in range(FRAME_COUNT):
            image = Image.new("RGB", (64, 48), (index * STEP, 40, 90))
            container.mux(stream.encode(av.VideoFrame.from_image(image)))
        container.mux(stream.encode(None))
    return path


def frame_index_of(path: str) -> int:
    """Which frame a written JPEG holds, read back out of its pixels."""
    with Image.open(path) as image:
        red = image.convert("RGB").getpixel((32, 24))[0]  # type: ignore[index]
    return round(red / STEP)


class TestExtractFrames:
    def test_every_stride_th_frame_from_start_and_each_file_is_that_frame(
        self, clip: Path, tmp_path: Path
    ) -> None:
        written = extract_frames(
            ExtractConfig(source=str(clip), start=2, count=4, stride=3), tmp_path
        )
        assert [index for index, _ in written] == [2, 5, 8, 11]
        # The file named frame 5 holds frame 5's pixels, not a neighbour's.
        assert [frame_index_of(path) for _, path in written] == [2, 5, 8, 11]
        assert all(path.endswith(".jpg") for _, path in written)

    def test_count_caps_the_run(self, clip: Path, tmp_path: Path) -> None:
        written = extract_frames(ExtractConfig(source=str(clip), count=3), tmp_path)
        assert [index for index, _ in written] == [0, 1, 2]

    def test_a_range_past_the_end_stops_at_the_last_frame(
        self, clip: Path, tmp_path: Path
    ) -> None:
        written = extract_frames(ExtractConfig(source=str(clip), start=10, count=50), tmp_path)
        assert [index for index, _ in written] == [10, 11]

    def test_a_second_extraction_reuses_the_files(self, clip: Path, tmp_path: Path) -> None:
        config = ExtractConfig(source=str(clip), count=2)
        first = extract_frames(config, tmp_path)
        stamp = Path(first[0][1]).stat().st_mtime_ns
        time.sleep(0.01)
        second = extract_frames(config, tmp_path)
        assert second == first
        assert Path(second[0][1]).stat().st_mtime_ns == stamp

    def test_cancelling_stops_early(self, clip: Path, tmp_path: Path) -> None:
        seen: list[int] = []
        written = extract_frames(
            ExtractConfig(source=str(clip), count=12),
            tmp_path,
            on_frame=lambda index, _path: seen.append(index),
            cancelled=lambda: len(seen) >= 3,
        )
        assert len(written) == 3

    def test_a_missing_video_is_a_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            extract_frames(ExtractConfig(source=str(tmp_path / "gone.mp4")), tmp_path)

    def test_a_file_that_is_not_a_video_is_refused(self, tmp_path: Path) -> None:
        fake = tmp_path / "notes.mp4"
        fake.write_text("not a video")
        with pytest.raises(VideoReadError):
            extract_frames(ExtractConfig(source=str(fake)), tmp_path / "out")


class TestConfig:
    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"start": -1}, "start"),
            ({"count": 0}, "count"),
            ({"stride": 0}, "stride"),
        ],
    )
    def test_bad_ranges_are_refused(self, kwargs: dict[str, int], message: str) -> None:
        with pytest.raises(ValueError, match=message):
            ExtractConfig(source="/v/a.mp4", **kwargs)

    def test_only_video_files(self) -> None:
        with pytest.raises(ValueError, match="Not a video"):
            ExtractConfig(source="/v/a.png")


class TestNaming:
    def test_two_videos_with_one_name_get_different_directories(self, tmp_path: Path) -> None:
        assert frames_dir(tmp_path, "/a/run1.mp4") != frames_dir(tmp_path, "/b/run1.mp4")
        assert frames_dir(tmp_path, "/a/run1.mp4").parent == tmp_path / "frames"

    def test_frame_files_carry_the_video_name(self) -> None:
        assert frame_filename("/a/run1.mp4", 12) == "run1-f000012.jpg"


class TestExtractor:
    def test_a_job_reports_its_frames_and_completes(self, clip: Path, tmp_path: Path) -> None:
        extractor = FrameExtractor()
        job = extractor.submit(
            ExtractConfig(source=str(clip), start=0, count=100, stride=4), tmp_path, FRAME_COUNT
        )
        # 0, 4, 8: the total is what the video can give, not the 100 asked for.
        assert job.total == 3
        deadline = time.monotonic() + 10
        while not job.finished and time.monotonic() < deadline:
            time.sleep(0.02)
        assert job.state == "complete"
        assert [index for index, _ in job.frames] == [0, 4, 8]

    def test_a_start_past_the_end_is_refused(self, clip: Path, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="past the last frame"):
            FrameExtractor().submit(
                ExtractConfig(source=str(clip), start=12), tmp_path, FRAME_COUNT
            )
