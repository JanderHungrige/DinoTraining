"""Tests for scripts/stage_msix.py (doc 151)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage_msix

NS = {
    "m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
    "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities",
}


@pytest.fixture
def build(tmp_path: Path) -> dict[str, Path]:
    exe = tmp_path / "target" / "dinotraining.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ")
    runtime = tmp_path / "runtime"
    (runtime / "backend" / "app").mkdir(parents=True)
    (runtime / "backend" / "app" / "main.py").write_text("")
    (runtime / "uv.exe").write_bytes(b"uv")
    icons = tmp_path / "icons"
    icons.mkdir()
    for logo in (*stage_msix.LOGOS, "icon.ico"):
        (icons / logo).write_bytes(b"png")
    identity = tmp_path / "identity.json"
    identity.write_text(json.dumps({
        "identity_name": "JanWerth.DinoTraining", "publisher": "CN=Jan & Co",
        "publisher_display_name": "Jan Werth",
    }))
    return {"exe": exe, "runtime": runtime, "icons": icons, "identity": identity, "out": tmp_path / "msix"}


def stage(build: dict[str, Path], version: str = "0.1.3") -> dict[str, str | bool]:
    return stage_msix.stage(build["exe"], version, build["out"], build["runtime"], build["icons"], build["identity"])


def test_the_package_holds_the_exe_the_runtime_the_logos_and_its_manifest(build: dict[str, Path]) -> None:
    stage(build)
    out = build["out"]
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert files == [
        "AppxManifest.xml",
        "Assets/Square150x150Logo.png",
        "Assets/Square44x44Logo.png",
        "Assets/StoreLogo.png",
        "DinoTraining.exe",
        "runtime/backend/app/main.py",
        "runtime/uv.exe",
    ]


def test_the_manifest_carries_identity_version_entry_point_and_capabilities(build: dict[str, Path]) -> None:
    stage(build, "0.1.3")
    root = ElementTree.parse(build["out"] / "AppxManifest.xml").getroot()
    identity = root.find("m:Identity", NS)
    assert identity is not None
    assert identity.attrib == {
        "Name": "JanWerth.DinoTraining", "Publisher": "CN=Jan & Co", "Version": "0.1.3.0", "ProcessorArchitecture": "x64",
    }
    application = root.find("m:Applications/m:Application", NS)
    assert application is not None
    assert application.attrib["Executable"] == "DinoTraining.exe"
    assert application.attrib["EntryPoint"] == "Windows.FullTrustApplication"
    capabilities = {c.attrib["Name"] for c in root.iter() if c.tag.endswith("Capability")}
    assert capabilities == {"internetClient", "runFullTrust"}
    assert root.findtext("m:Properties/m:PublisherDisplayName", namespaces=NS) == "Jan Werth"


@pytest.mark.parametrize("version", ["0.1", "0.1.3.1", "v0.1.3", "0.1.3-beta"])
def test_only_three_number_versions(build: dict[str, Path], version: str) -> None:
    with pytest.raises(stage_msix.StageError, match="three numbers"):
        stage(build, version)


def test_what_the_package_cannot_be_made_without_is_named(build: dict[str, Path]) -> None:
    (build["icons"] / "StoreLogo.png").unlink()
    with pytest.raises(stage_msix.StageError, match="StoreLogo.png"):
        stage(build)
    build["exe"].unlink()
    with pytest.raises(stage_msix.StageError, match="No app executable"):
        stage(build)


def test_an_identity_without_a_publisher_dn_is_refused(build: dict[str, Path]) -> None:
    build["identity"].write_text(json.dumps({"identity_name": "X", "publisher": "Jan", "publisher_display_name": "Jan"}))
    with pytest.raises(stage_msix.StageError, match="CN="):
        stage(build)


def test_the_repository_identity_is_marked_as_a_placeholder() -> None:
    identity = stage_msix.read_identity()
    assert identity["placeholder"] is True  # until Jan reserves the name (doc 151)
    ElementTree.fromstring(stage_msix.manifest("0.1.3", identity).encode())
