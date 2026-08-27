"""One contract over a folder and a video file (doc 68).

The point of `FrameSequence` is that nothing downstream can tell which it is. So the tests
that matter run the *same* assertions against both kinds, and the ones that differ are
the ones where the difference is real and deliberately exposed — a folder has no frame rate.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.ml.images import FolderNotFoundError
from app.ml.video.decode import VideoReadError
from app.ml.video.sequence import frame_image, frame_range, open_sequence

FRAME_COUNT = 8
STEP = 20


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """Eight PNGs whose red channel encodes their position."""
    directory = tmp_path / "frames"
    directory.mkdir()
    for index in range(FRAME_COUNT):
        Image.new("RGB", (32, 24), (index * STEP, 10, 10)).save(
            directory / f"frame_{index:03d}.png"
        )
    return directory


@pytest.fixture
def clip(tmp_path: Path) -> Path:
    import av

    path = tmp_path / "clip.mp4"
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=5)
        stream.width, stream.height = 32, 24
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "0", "preset": "ultrafast"}
        for index in range(FRAME_COUNT):
            image = Image.new("RGB", (32, 24), (index * STEP, 10, 10))
            container.mux(stream.encode(av.VideoFrame.from_image(image)))
        container.mux(stream.encode(None))
    return path


def frame_index_of(image: Image.Image) -> int:
    """Which frame this is. Rounded — H.264 does not round-trip RGB exactly."""
    return round(image.getpixel((16, 12))[0] / STEP)  # type: ignore[index]


class TestBothKindsAnswerTheSameQuestions:
    """Every assertion here is run against a folder *and* a video, because a caller that
    could tell them apart is the thing this abstraction exists to prevent."""

    @pytest.fixture(params=["folder", "clip"])
    def sequence(self, request: pytest.FixtureRequest):
        return open_sequence(str(request.getfixturevalue(request.param)))

    def test_it_reports_how_many_frames(self, sequence) -> None:
        assert sequence.frames == FRAME_COUNT

    def test_it_reports_the_size(self, sequence) -> None:
        assert (sequence.width, sequence.height) == (32, 24)

    def test_it_serves_the_frame_asked_for(self, sequence) -> None:
        for index in (0, 3, FRAME_COUNT - 1):
            assert frame_index_of(frame_image(sequence, index)) == index

    def test_frames_come_back_in_rgb(self, sequence) -> None:
        assert frame_image(sequence, 0).mode == "RGB"

    def test_a_frame_past_the_end_is_refused(self, sequence) -> None:
        # Range-checked here rather than in the decoder: asking a video for frame 10^9
        # walks the entire file before failing, which is a request that never returns.
        with pytest.raises(IndexError):
            frame_image(sequence, FRAME_COUNT)

    def test_a_negative_frame_is_refused(self, sequence) -> None:
        with pytest.raises(IndexError):
            frame_image(sequence, -1)


class TestWhereTheyHonestlyDiffer:
    def test_a_folder_has_no_frame_rate(self, folder: Path) -> None:
        """Exposed rather than filled in. Claiming 30 fps for a folder would put a number
        on screen that came from nowhere and drive a playback speed nobody chose."""
        assert open_sequence(str(folder)).fps is None

    def test_a_folder_has_no_duration_either(self, folder: Path) -> None:
        assert open_sequence(str(folder)).duration is None

    def test_a_video_reports_its_rate_and_duration(self, clip: Path) -> None:
        sequence = open_sequence(str(clip))
        assert sequence.fps == pytest.approx(5)
        assert sequence.duration == pytest.approx(FRAME_COUNT / 5)

    def test_a_folder_frame_keeps_its_filename(self, folder: Path) -> None:
        # A real path the user can open. The prepass records it per prediction.
        assert open_sequence(str(folder)).label(3) == "frame_003.png"

    def test_a_video_frame_is_named_by_position(self, clip: Path) -> None:
        """It has no filename, and inventing one would be a name that does not exist."""
        assert open_sequence(str(clip)).label(3) == "frame 3"


class TestWhatItRefusesToOpen:
    def test_an_empty_folder(self, tmp_path: Path) -> None:
        empty = tmp_path / "nothing"
        empty.mkdir()
        with pytest.raises(FolderNotFoundError):
            open_sequence(str(empty))

    def test_a_folder_of_non_images(self, tmp_path: Path) -> None:
        directory = tmp_path / "docs"
        directory.mkdir()
        (directory / "notes.txt").write_text("hello")
        with pytest.raises(FolderNotFoundError):
            open_sequence(str(directory))

    def test_a_file_that_is_neither(self, tmp_path: Path) -> None:
        odd = tmp_path / "thing.bin"
        odd.write_bytes(b"\x00\x01")
        with pytest.raises(VideoReadError, match="Not a video"):
            open_sequence(str(odd))

    def test_a_path_that_does_not_exist(self, tmp_path: Path) -> None:
        with pytest.raises(FolderNotFoundError):
            open_sequence(str(tmp_path / "absent"))


class TestTheRange:
    @pytest.fixture
    def sequence(self, folder: Path):
        return open_sequence(str(folder))

    def test_it_covers_what_was_asked_for(self, sequence) -> None:
        assert list(frame_range(sequence, 2, 3)) == [2, 3, 4]

    def test_it_clamps_to_the_end_rather_than_refusing(self, sequence) -> None:
        """Asking for 200 frames from frame 6 of an 8-frame sequence is not a mistake — it
        is someone asking for "the rest", and the rest is what they meant."""
        assert list(frame_range(sequence, 6, 200)) == [6, 7]

    def test_a_start_past_the_end_is_refused(self, sequence) -> None:
        # This one *is* a mistake: there is no "rest" to give.
        with pytest.raises(ValueError, match="past the last frame"):
            frame_range(sequence, FRAME_COUNT, 5)

    def test_a_negative_start_is_refused(self, sequence) -> None:
        with pytest.raises(ValueError, match="negative"):
            frame_range(sequence, -1, 5)

    def test_a_zero_count_is_refused(self, sequence) -> None:
        # An empty run would finish instantly and report success over nothing.
        with pytest.raises(ValueError, match="at least 1"):
            frame_range(sequence, 0, 0)

    def test_the_whole_sequence_is_the_default_shape(self, sequence) -> None:
        assert list(frame_range(sequence, 0, FRAME_COUNT)) == list(range(FRAME_COUNT))
