"""Download an example into the app's data folder, unpacking while it streams (doc 138).

The folder is written as `<name>.part` and renamed when complete, so a broken download
never looks finished, and a finished one is reused instead of downloaded again.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx

from app import __version__
from app.core.config import Settings
from app.core.paths import free_disk_bytes
from app.datasets.db import data_root
from app.datasets.examples.catalogue import VARIANTS, Example, Variant, keeps
from app.datasets.examples.zipstream import stream_unzip

logger = logging.getLogger(__name__)

USER_AGENT = f"DinoTraining/{__version__} (+https://github.com/JanderHungrige/DinoTraining)"
_SPARE = 1 << 30
_CHUNK = 1 << 16
#: Bytes read so far, of how many, and the member passing.
Progress = Callable[[int, int, str], None]
Chunks = Callable[[str], Iterator[bytes]]


def examples_dir(settings: Settings | None = None) -> Path:
    return data_root(settings) / "examples"


def target_dir(example: Example, variant: Variant, settings: Settings | None = None) -> Path:
    return examples_dir(settings) / f"{example.sequence}-{variant}"


def downloaded(example: Example, settings: Settings | None = None) -> list[Variant]:
    return [variant for variant in VARIANTS if target_dir(example, variant, settings).is_dir()]


def http_chunks(url: str) -> Iterator[bytes]:
    """The response body in chunks; an honest user agent, no disguise (doc 138)."""
    timeout = httpx.Timeout(30.0, read=120.0)
    headers = {"User-Agent": USER_AGENT}
    with httpx.stream("GET", url, headers=headers, timeout=timeout, follow_redirects=True) as reply:
        if reply.status_code != 200:
            raise ValueError(
                f"The download server answered {reply.status_code}. "
                f"Download it by hand from the portal and import the folder."
            )
        yield from reply.iter_bytes(_CHUNK)


def fetch(
    example: Example,
    variant: Variant,
    progress: Progress,
    settings: Settings | None = None,
    chunks: Chunks = http_chunks,
) -> Path:
    """The example's unpacked folder, downloading it first if it is not there yet."""
    target = target_dir(example, variant, settings)
    if target.is_dir():
        return target
    _check_space(example, variant, target)
    partial = target.with_name(target.name + ".part")
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    total = example.download_bytes
    try:
        result = stream_unzip(
            chunks(example.url),
            partial,
            lambda member: keeps(variant, member),
            lambda done, member: progress(done, total, member),
        )
    except (httpx.HTTPError, OSError) as error:
        logger.warning("Download of %s failed: %s", example.url, error)
        shutil.rmtree(partial, ignore_errors=True)
        raise ValueError(f"The download broke off ({error}). Try again.") from error
    except ValueError:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    logger.info(
        "Example %s (%s): kept %d files (%d MB), skipped %d, read %d MB",
        example.sequence,
        variant,
        result.kept,
        result.kept_bytes >> 20,
        result.skipped,
        result.read_bytes >> 20,
    )
    partial.rename(target)
    return target


def _check_space(example: Example, variant: Variant, target: Path) -> None:
    needed = (
        example.download_bytes if variant == "full" else example.download_bytes // 10
    ) + _SPARE
    free = free_disk_bytes(target)
    if free < needed:
        raise ValueError(
            f"Not enough free disk space: {needed >> 20} MB needed, {free >> 20} MB free."
        )
