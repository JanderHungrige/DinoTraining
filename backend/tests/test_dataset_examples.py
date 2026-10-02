"""Doc 138: the OSDaR23 example — download (faked), keep per variant, import, API."""

from __future__ import annotations

import io
import time
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.datasets.examples.catalogue import OSDAR23, description, keeps
from app.datasets.examples.fetch import fetch, target_dir
from app.datasets.intake.detect import scan
from app.datasets.intake.jobs import ImportJob, ImportJobs
from tests import intake_fixtures as fx


@pytest.fixture(autouse=True)
def _data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.datasets.db import reset_connection

    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_connection()


def osdar_like(tmp_path: Path) -> bytes:
    """Doc 136's OpenLABEL fixture, plus what the real archive has around it: an
    unannotated side camera, lidar, and the readme's preview picture."""
    root = fx.openlabel(tmp_path / "src")
    fx.picture(root / "rgb_left" / "000.png")
    fx.picture(root / "rgb_left" / "001.png")
    fx.picture(root / "readme_img" / "preview.png")
    fx.picture(root / "radar" / "000.png")  # OSDaR23 renders its radar as PNG
    (root / "lidar").mkdir()
    (root / "lidar" / "000.pcd").write_bytes(b"pcd" * 100)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zipped.write(path, path.relative_to(root).as_posix())
    return buffer.getvalue()


def feeder(data: bytes, calls: list[str]):  # type: ignore[no-untyped-def]
    def chunks(url: str) -> Iterator[bytes]:
        calls.append(url)
        yield from (data[i : i + 997] for i in range(0, len(data), 997))

    return chunks


def files(folder: Path) -> list[str]:
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())


def test_the_variants_keep_what_jan_asked_for() -> None:
    assert keeps("rgb-center", "rgb_center/012_1631.png")
    assert keeps("rgb-center", "3_fire_site_3.4_labels.json")
    assert not keeps("rgb-center", "rgb_highres_center/012.png")
    assert not keeps("rgb-center", "lidar/012.pcd")
    assert keeps("full", "lidar/012.pcd") and keeps("full", "radar/x.csv")
    assert not keeps("full", "readme_img/preview.png")
    text = description(OSDAR23, "rgb-center")
    assert "CC BY-SA 3.0 DE" in text and "DZSF" in text and "10.57806/9mv146r0" in text
    assert "annotations: CC0 1.0" in text


def test_fetch_keeps_per_variant_and_reuses_a_finished_folder(tmp_path: Path) -> None:
    data = osdar_like(tmp_path)
    calls: list[str] = []
    seen: list[tuple[int, int]] = []
    centre = fetch(
        OSDAR23, "rgb-center", lambda d, t, _m: seen.append((d, t)), None, feeder(data, calls)
    )
    assert files(centre) == ["rgb_center/000.png", "rgb_center/001.png", "seq_labels.json"]
    assert (
        centre == target_dir(OSDAR23, "rgb-center")
        and not centre.with_name(centre.name + ".part").exists()
    )
    assert seen and all(total == OSDAR23.download_bytes for _d, total in seen)
    full = fetch(OSDAR23, "full", lambda *_: None, None, feeder(data, calls))
    assert "lidar/000.pcd" in files(full) and "rgb_left/000.png" in files(full)
    assert not any(name.startswith("readme_img/") for name in files(full))
    assert fetch(OSDAR23, "rgb-center", lambda *_: None, None, feeder(data, calls)) == centre
    assert calls == [OSDAR23.url, OSDAR23.url]  # the third call downloaded nothing


def test_a_broken_download_leaves_no_folder(tmp_path: Path) -> None:
    data = osdar_like(tmp_path)
    with pytest.raises(ValueError, match="ended in the middle"):
        fetch(OSDAR23, "full", lambda *_: None, None, feeder(data[: len(data) // 2], []))
    target = target_dir(OSDAR23, "full")
    assert not target.exists() and not target.with_name(target.name + ".part").exists()


def test_a_camera_without_one_annotation_is_not_annotated(tmp_path: Path) -> None:
    full = fetch(OSDAR23, "full", lambda *_: None, None, feeder(osdar_like(tmp_path), []))
    detection, documents, _ = scan(full)
    assert detection.kind == "openlabel" and len(documents) == 1  # rgb_center only
    assert (detection.annotated_pictures, detection.uncovered) == (2, 2)
    assert detection.pictures == 4  # the radar's rendering is not a picture


def _finish(jobs: ImportJobs, job: ImportJob) -> ImportJob:
    for _ in range(200):
        if job.state != "running":
            return job
        time.sleep(0.05)
    raise AssertionError("the job did not finish")


def test_the_job_downloads_then_imports_and_a_second_click_joins_it(tmp_path: Path) -> None:
    from app.datasets.intake.profile import dataset_profile

    jobs = ImportJobs()
    chunks = feeder(osdar_like(tmp_path), [])
    job = jobs.submit_example(OSDAR23, "full", None, chunks)
    assert job.phase == "download"
    assert jobs.submit_example(OSDAR23, "full", None, chunks) is job
    assert jobs.running_example("osdar23") in (job, None)  # None once it has finished
    done = _finish(jobs, job)
    assert done.state == "complete" and done.phase == "import", done.error
    assert done.result is not None
    assert (done.result.pictures, done.result.annotated_pictures) == (4, 2)
    assert done.result.name == "OSDaR23 · 3_fire_site_3.4 · all sensors"
    profile = dataset_profile(done.result.dataset_id)
    assert profile.description is not None and "CC BY-SA 3.0 DE" in profile.description
    assert profile.classes == ["person"]


def test_the_api_lists_the_example_and_starts_its_job(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.datasets.intake import jobs as jobs_module
    from app.main import create_app

    started: list[str] = []

    def fake(self: ImportJobs, example, variant, settings=None, chunks=None):  # type: ignore[no-untyped-def]
        started.append(variant)
        return ImportJob(job_id="j1", path=example.url, phase="download", example="x")

    monkeypatch.setattr(jobs_module.ImportJobs, "submit_example", fake)
    client = TestClient(create_app())
    listed = client.get("/api/v1/datasets/examples").json()["examples"]
    assert [entry["example_id"] for entry in listed] == ["osdar23"]
    assert listed[0]["licence"] == "CC BY-SA 3.0 DE" and listed[0]["downloaded"] == []
    assert listed[0]["running_job"] is None
    reply = client.post("/api/v1/datasets/examples/osdar23/import", json={"variant": "rgb-center"})
    assert reply.status_code == 202 and reply.json()["phase"] == "download"
    assert started == ["rgb-center"]
    running = ImportJob(job_id="j2", path="", phase="download", example="osdar23/full")
    monkeypatch.setattr(jobs_module.ImportJobs, "running_example", lambda self, _id: running)
    assert client.get("/api/v1/datasets/examples").json()["examples"][0]["running_job"] == "j2"
    assert (
        client.post("/api/v1/datasets/examples/nope/import", json={"variant": "full"}).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/datasets/examples/osdar23/import", json={"variant": "lidar"}
        ).status_code
        == 422
    )
