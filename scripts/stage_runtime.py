"""Stage the app's bundled runtime (doc 126): uv, the backend source and its lock.

    python scripts/stage_runtime.py <target-triple>

writes apps/desktop/src-tauri/runtime/, which tauri.release.conf.json bundles as a
resource. Everything else — Python itself, torch, the rest — is installed on the user's
machine from the official sources at first start (doc 127), exactly as uv.lock pins it.

Standard library only: this runs on all three CI platforms before anything is installed.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

#: Pinned; bump deliberately. Its archives are verified against the release's .sha256.
UV_VERSION = "0.12.21"
TARGETS = {
    "aarch64-apple-darwin": "uv-aarch64-apple-darwin.tar.gz",
    "x86_64-pc-windows-msvc": "uv-x86_64-pc-windows-msvc.zip",
    "x86_64-unknown-linux-gnu": "uv-x86_64-unknown-linux-gnu.tar.gz",
}
REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
OUT = REPO / "apps" / "desktop" / "src-tauri" / "runtime"
#: What of the backend ships: the package and the two files uv needs. Never tests, caches,
#: a venv, or anything a developer happens to have lying in backend/.
SHIPPED_FILES = ("pyproject.toml", "uv.lock")
SKIPPED_DIRS = {"__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        data: bytes = response.read()
    return data


def fetch_uv(target: str) -> bytes:
    """The uv binary for `target`, verified against the release's published checksum."""
    name = TARGETS[target]
    base = f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/{name}"
    archive = _fetch(base)
    expected = _fetch(f"{base}.sha256").decode().split()[0]
    actual = hashlib.sha256(archive).hexdigest()
    if actual != expected:
        raise SystemExit(
            f"uv {UV_VERSION} for {target}: checksum {actual} != {expected}"
        )
    binary = "uv.exe" if name.endswith(".zip") else "uv"
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            name_in_zip = next(n for n in zipped.namelist() if n.endswith(binary))
            return zipped.read(name_in_zip)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tarred:
        member = next(m for m in tarred.getmembers() if m.name.endswith(f"/{binary}"))
        extracted = tarred.extractfile(member)
        assert extracted is not None
        return extracted.read()


def copy_backend(destination: Path) -> int:
    """The backend package and uv's two files. Returns the number of files copied."""
    count = 0
    for source in (BACKEND / "app").rglob("*"):
        if source.is_dir() or SKIPPED_DIRS & set(source.parts):
            continue
        target = destination / source.relative_to(BACKEND)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        count += 1
    for name in SHIPPED_FILES:
        shutil.copy2(BACKEND / name, destination / name)
        count += 1
    return count


def stage(target: str, out: Path = OUT) -> dict[str, object]:
    if target not in TARGETS:
        raise SystemExit(f"Unknown target {target}; one of {', '.join(TARGETS)}")
    if out.exists():
        shutil.rmtree(out)
    (out / "backend").mkdir(parents=True)
    files = copy_backend(out / "backend")
    binary = "uv.exe" if target.endswith("msvc") else "uv"
    uv = out / binary
    uv.write_bytes(fetch_uv(target))
    uv.chmod(0o755)
    lock = (out / "backend" / "uv.lock").read_bytes()
    version = {
        "uv": UV_VERSION,
        "target": target,
        "lock_sha256": hashlib.sha256(lock).hexdigest(),
        "backend_files": files,
    }
    (out / "VERSION.json").write_text(
        json.dumps(version, indent=2) + "\n", encoding="utf-8"
    )
    return version


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(json.dumps(stage(sys.argv[1]), indent=2))
