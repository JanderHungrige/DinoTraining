"""Decoding frames out of a real video file (doc 68).

**Encoded on the fly rather than mocked.** A stubbed decoder would pass while proving
nothing about the one property this module exists for — that frame *N* back is frame *N*,
not the keyframe near it. So these write a real mp4 whose frames are individually
identifiable and then ask for them out of order.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.ml.video.decode import (
    VIDEO_SUFFIXES,
    VideoReadError,
    looks_like_video,
    probe,
    read_frame,
)

#: Each frame is a flat colour whose red channel encodes its index, so a decoded frame can
#: be asked "which one are you?" without trusting the codec to be exact.
FRAME_COUNT = 12
FPS = 6


@pytest.fixture(scope="module")
def clip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real H.264 mp4 with individually identifiable frames."""
    import av

    path = tmp_path_factory.mktemp("video") / "clip.mp4"
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=FPS)
        stream.width, stream.height = 64, 48
        # yuv420p, which is what a camera or a screen recorder actually writes — so the
        # fixture exercises the format the app will really meet.
        #
        # H.264 does **not** round-trip RGB exactly, even lossless: the RGB->YUV matrix at
        # limited range (16-235) costs a level or two, and a flat red 40 comes back 39.
        # Measured, not assumed — yuv444p and full-range were both tried and neither fixes
        # it. So `frame_index_of` rounds instead of comparing exactly. The property under
        # test is *which frame came back*, and with frames 20 apart that is unambiguous at
        # any plausible codec error; demanding bit-equality would be testing libx264.
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "0", "preset": "ultrafast"}

        for index in range(FRAME_COUNT):
            image = Image.new("RGB", (64, 48), (index * STEP, 40, 90))
            frame = av.VideoFrame.from_image(image)
            container.mux(stream.encode(frame))
        container.mux(stream.encode(None))
    return path


#: How far apart two frames' identifying values are. Large enough that codec error can
#: never turn one frame into its neighbour.
STEP = 20


def frame_index_of(image: Image.Image) -> int:
    """Which frame this is, read back out of its own pixels.

    Rounded rather than compared exactly — see the fixture. Read from the middle of the
    frame so no edge artefact is involved.
    """
    red = image.getpixel((32, 24))[0]  # type: ignore[index]
    return round(red / STEP)


class TestProbe:
    def test_it_reports_the_frame_count(self, clip: Path) -> None:
        assert probe(str(clip)).frames == FRAME_COUNT

    def test_it_reports_the_frame_rate(self, clip: Path) -> None:
        assert probe(str(clip)).fps == pytest.approx(FPS)

    def test_it_reports_the_size(self, clip: Path) -> None:
        info = probe(str(clip))
        assert (info.width, info.height) == (64, 48)

    def test_duration_agrees_with_frames_and_rate(self, clip: Path) -> None:
        """Derived rather than read off the container, so the three can never disagree —
        a duration that contradicts the frame count makes the range control lie."""
        info = probe(str(clip))
        assert info.duration == pytest.approx(FRAME_COUNT / FPS)

    def test_a_missing_file_is_a_file_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            probe(str(tmp_path / "nope.mp4"))

    def test_a_file_that_is_not_a_video_is_refused(self, tmp_path: Path) -> None:
        # A .mp4 that is actually text. Reported as unreadable, not as a 500.
        fake = tmp_path / "fake.mp4"
        fake.write_text("this is not a video")
        with pytest.raises(VideoReadError):
            probe(str(fake))


class TestReadFrame:
    def test_it_returns_the_frame_asked_for(self, clip: Path) -> None:
        """The property the whole module exists for. A seek would land on the nearest
        keyframe and return a frame *near* this one — invisible until an overlay computed
        for frame 7 is drawn over frame 4 and every box trails the object."""
        for index in (0, 3, 7, FRAME_COUNT - 1):
            assert frame_index_of(read_frame(str(clip), index)) == index

    def test_frames_can_be_asked_for_out_of_order(self, clip: Path) -> None:
        # Scrubbing backwards is the normal case in a player, and a decoder that only
        # works forwards would appear to work until someone dragged the slider left.
        assert frame_index_of(read_frame(str(clip), 9)) == 9
        assert frame_index_of(read_frame(str(clip), 2)) == 2

    def test_the_frame_is_rgb(self, clip: Path) -> None:
        # Every consumer downstream assumes RGB; a YUV or palette frame would reach a
        # model as the wrong colours rather than as an error.
        assert read_frame(str(clip), 0).mode == "RGB"

    def test_a_frame_past_the_end_is_refused(self, clip: Path) -> None:
        with pytest.raises(VideoReadError, match="no frame"):
            read_frame(str(clip), FRAME_COUNT + 5)

    def test_a_negative_index_is_refused_before_any_decoding(self, clip: Path) -> None:
        # Python would otherwise never match it and walk the entire file first.
        with pytest.raises(VideoReadError, match="negative"):
            read_frame(str(clip), -1)


class TestWhatCountsAsAVideo:
    def test_it_recognises_the_common_containers(self) -> None:
        for suffix in (".mp4", ".mov", ".mkv", ".webm"):
            assert looks_like_video(Path(f"a{suffix}"))

    def test_it_is_case_insensitive(self) -> None:
        # A camera writing .MOV is not an exotic case.
        assert looks_like_video(Path("CLIP.MOV"))

    def test_an_image_is_not_a_video(self) -> None:
        assert not looks_like_video(Path("frame.png"))

    def test_the_list_is_short_on_purpose(self) -> None:
        """Every entry is something a camera or screen recorder writes. A longer list is a
        longer list of ways to find out at decode time that ffmpeg lacks the codec."""
        assert len(VIDEO_SUFFIXES) <= 8
