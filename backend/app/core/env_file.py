"""Reading and writing the ``.env`` file the app actually loads.

Two things this module exists to guarantee.

**One resolved location.** ``SettingsConfigDict(env_file=".env")`` resolves relative to the
*working directory*, so a backend started from ``backend/`` looked for ``backend/.env`` and
silently ignored the real file at the repository root — every setting fell back to its
default and nothing said so. The path is now absolute and computed once, here.

**The token is never echoed.** Values written here are secrets. Nothing in this module logs
a value, and the read side returns a masked hint rather than the token.
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

#: Override for packaging and tests. Wave 8 will point this at the per-user config
#: directory; the test suite points it at a throwaway path so a developer's real
#: credentials can never leak into a test run.
ENV_FILE_VAR = "DINO_ENV_FILE"

#: Owner read/write only. A token in a world-readable file is a token on the floor.
_SECRET_MODE = stat.S_IRUSR | stat.S_IWUSR


def env_file_path() -> Path:
    """Absolute path to the ``.env`` this process reads and writes.

    Resolution order: an explicit ``DINO_ENV_FILE``, otherwise the repository root — the
    directory containing ``backend/``, derived from this file's location rather than from
    the working directory, because the working directory is what broke it.
    """
    override = os.environ.get(ENV_FILE_VAR)
    if override:
        return Path(override).expanduser().resolve()
    # .../backend/app/core/env_file.py -> core -> app -> backend -> repo root
    return Path(__file__).resolve().parents[3] / ".env"


def read_env(path: Path | None = None) -> dict[str, str]:
    """Parse the file into a plain dict. Missing file is an empty dict, not an error."""
    target = path or env_file_path()
    if not target.is_file():
        return {}

    values: dict[str, str] = {}
    for line in target.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def write_env_value(key: str, value: str, path: Path | None = None) -> Path:
    """Set one key, preserving every other line, comment and blank line in the file.

    Rewriting the file from a parsed dict would silently delete the user's comments and
    reorder their keys. The file is theirs; this touches one line of it.
    """
    target = path or env_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    lines = target.read_text(encoding="utf-8").splitlines() if target.is_file() else []
    replacement = f"{key}={value}"
    replaced = False

    for index, line in enumerate(lines):
        candidate = line.strip()
        if candidate.startswith("#") or "=" not in candidate:
            continue
        if candidate.partition("=")[0].strip() == key:
            lines[index] = replacement
            replaced = True
            break

    if not replaced:
        lines.append(replacement)

    # Write, then tighten permissions — the file may be created by this call.
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    target.chmod(_SECRET_MODE)

    # Deliberately logs the key and never the value.
    logger.info("Updated %s in %s", key, target)
    return target


def mask_secret(value: str | None) -> str | None:
    """A hint that identifies a token without disclosing it.

    Returns at most the last four characters. Short values are masked entirely rather than
    partially revealed, since four characters of an eight-character secret is half of it.
    """
    if not value:
        return None
    if len(value) <= 8:
        return "•" * len(value)
    return f"{'•' * 4}{value[-4:]}"
