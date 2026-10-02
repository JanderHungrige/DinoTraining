"""Render the Homebrew formula for one release (doc 130).

    python scripts/render_formula.py <version> <sha256> > v-rex.rb

The release workflow runs this for the macOS archive it just built and attaches the
result to the release; Jan copies it into the tap. Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "packaging"
    / "homebrew"
    / "v-rex.rb.template"
)
VERSION = re.compile(r"^\d+\.\d+\.\d+([-.][0-9A-Za-z.]+)?$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def render(version: str, sha256: str, template: str | None = None) -> str:
    # Not str.removeprefix: this also runs on the Mac's system Python 3.8.
    version = version[1:] if version.startswith("v") else version
    if not VERSION.match(version):
        raise SystemExit(f"Not a release version: {version!r}")
    if not SHA256.match(sha256):
        raise SystemExit(f"Not a sha256: {sha256!r}")
    text = TEMPLATE.read_text(encoding="utf-8") if template is None else template
    rendered = text.replace("{{version}}", version).replace("{{sha256}}", sha256)
    if "{{" in rendered:
        raise SystemExit("The template has a placeholder this script does not fill")
    return rendered


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    sys.stdout.write(render(sys.argv[1], sys.argv[2]))
