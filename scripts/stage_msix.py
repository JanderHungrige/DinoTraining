"""Stage the Store edition's MSIX contents (doc 151): exe, runtime, logos, manifest.

    python scripts/stage_msix.py --exe <dinotraining.exe> --version 0.1.3 --out <dir>

The release workflow packs the result with `makeappx pack /d <dir>`. The identity comes
from packaging/msix/identity.json: the identity Jan reserved for V-Rex in Partner
Center (doc 159).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from xml.etree import ElementTree

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "packaging" / "msix" / "AppxManifest.template.xml"
IDENTITY = REPO / "packaging" / "msix" / "identity.json"
RUNTIME = REPO / "apps" / "desktop" / "src-tauri" / "runtime"
ICONS = REPO / "apps" / "desktop" / "src-tauri" / "icons"
LOGOS = ("Square44x44Logo.png", "Square150x150Logo.png", "StoreLogo.png")
EXE_NAME = "V-Rex.exe"


class StageError(ValueError):
    """Something the package cannot be made without."""


def msix_version(version: str) -> str:
    """`0.1.3` → `0.1.3.0`: the Store requires four parts with the last one 0."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise StageError(f"The version must be three numbers, not {version!r}.")
    return f"{version}.0"


def read_identity(path: Path = IDENTITY) -> dict[str, str | bool]:
    identity = json.loads(path.read_text(encoding="utf-8"))
    for key in ("identity_name", "publisher", "publisher_display_name"):
        if not str(identity.get(key, "")).strip():
            raise StageError(f"{path.name} has no {key}.")
    if not str(identity["publisher"]).startswith("CN="):
        raise StageError("The publisher must be a distinguished name starting with CN=.")
    return identity


def manifest(version: str, identity: dict[str, str | bool], template: Path = TEMPLATE) -> str:
    text = template.read_text(encoding="utf-8")
    for key, value in (
        ("identity_name", identity["identity_name"]),
        ("publisher", identity["publisher"]),
        ("publisher_display_name", identity["publisher_display_name"]),
        ("version", msix_version(version)),
    ):
        text = text.replace("{" + key + "}", _xml(str(value)))
    ElementTree.fromstring(text.encode("utf-8"))  # well-formed, or this raises
    return text


def _xml(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def stage(
    exe: Path,
    version: str,
    out: Path,
    runtime: Path = RUNTIME,
    icons: Path = ICONS,
    identity_file: Path = IDENTITY,
) -> dict[str, str | bool]:
    """Write the package's folder; returns the identity used."""
    if not exe.is_file():
        raise StageError(f"No app executable at {exe}.")
    if not (runtime / "backend").is_dir():
        raise StageError(f"No staged runtime at {runtime} (run stage_runtime.py first).")
    missing = [logo for logo in LOGOS if not (icons / logo).is_file()]
    if missing:
        raise StageError(f"Logos missing in {icons}: {', '.join(missing)}.")
    identity = read_identity(identity_file)
    text = manifest(version, identity)
    if out.exists():
        shutil.rmtree(out)
    (out / "Assets").mkdir(parents=True)
    shutil.copy2(exe, out / EXE_NAME)
    shutil.copytree(runtime, out / "runtime")
    for logo in LOGOS:
        shutil.copy2(icons / logo, out / "Assets" / logo)
    (out / "AppxManifest.xml").write_text(text, encoding="utf-8")
    return identity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        identity = stage(args.exe, args.version, args.out)
    except StageError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    note = " (placeholder identity: reserve the name in Partner Center)" if identity.get("placeholder") else ""
    print(f"Staged {args.out} as {identity['identity_name']} {msix_version(args.version)}{note}")
    print(f"publisher={identity['publisher']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
