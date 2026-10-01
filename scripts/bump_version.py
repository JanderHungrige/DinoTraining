"""Set the app's version everywhere it is written (doc 133: a merge to main with a new
version is a release).

    python scripts/bump_version.py 0.2.0

The release workflow reads tauri.conf.json; the backend reports app.__version__ in
/health; the rest must agree or the installer, the app and its about box disagree.
Afterwards: `cd backend && uv lock` (the lock records the backend's own version).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

#: (file, pattern whose group 1 is the version) — each must match exactly once.
TEXT_FILES: tuple[tuple[str, str], ...] = (
    ("apps/desktop/src-tauri/Cargo.toml", r'(?m)^version = "([^"]+)"'),
    ("backend/pyproject.toml", r'(?m)^version = "([^"]+)"'),
    ("backend/app/__init__.py", r'(?m)^__version__ = "([^"]+)"'),
)
#: (file, how many leading "version" fields are the app's own): a package-lock.json
#: carries it at its top and again under packages[""].
JSON_FILES: tuple[tuple[str, int], ...] = (
    ("apps/desktop/src-tauri/tauri.conf.json", 1),
    ("apps/desktop/package.json", 1),
    ("apps/frontend/package.json", 1),
    ("apps/desktop/package-lock.json", 2),
    ("apps/frontend/package-lock.json", 2),
)


def bump(version: str, repo: Path = REPO) -> list[str]:
    if not SEMVER.match(version):
        raise SystemExit(f"Not a version like 1.2.3: {version!r}")
    changed: list[str] = []
    for name, pattern in TEXT_FILES:
        path = repo / name
        text = path.read_text(encoding="utf-8")
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            raise SystemExit(f"{name}: expected one version line, found {len(matches)}")
        start, end = matches[0].span(1)
        path.write_text(text[:start] + version + text[end:], encoding="utf-8")
        changed.append(name)
    for name, count in JSON_FILES:
        path = repo / name
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if "version" not in data:
            raise SystemExit(f"{name}: no version field")
        # The leading "version" values only (dependencies follow), keeping the formatting.
        new = re.sub(
            r'("version"\s*:\s*")[^"]+(")', rf"\g<1>{version}\g<2>", text, count=count
        )
        path.write_text(new, encoding="utf-8")
        changed.append(name)
    return changed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    for name in bump(sys.argv[1]):
        print("set", sys.argv[1], "in", name)
