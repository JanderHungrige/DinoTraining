"""Importing a community head — the untrusted half of doc 15.

This is the app's only boundary that accepts a model source chosen by the user, so it
is the only place a stranger's bytes get near a model loader. Two rules carry the
weight:

* ``repo_id`` is validated as a plain ``owner/name`` before it is used for anything;
* the repo must publish **safetensors**. A ``.pt``/``.pth`` is refused outright rather
  than verified-then-loaded, because nothing about a stranger's repo can make
  ``torch.load`` safe — it is arbitrary code execution in an app installed by people
  who did not write it.

There is deliberately no "prefer safetensors, fall back to pickle" branch. A fallback
is reachable by anyone who can name a repo, which makes it the only branch that
matters to an attacker.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from torch import Tensor

from app.core.config import Settings, get_settings
from app.ml.backbone import read_capabilities
from app.ml.heads.instances import HeadInstance
from app.ml.heads.register import (
    IncompatibleHeadError,
    register_head,
    require_compatible,
    require_spec,
)

logger = logging.getLogger(__name__)

#: HuggingFace repo ids are ``owner/name``. Anchored, exactly one slash, each segment
#: starting alphanumeric. A whitelist rather than a blacklist of traversal-looking
#: strings, because this value is fully attacker-controlled.
_REPO_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")

#: Extensions that mean "pickle". Detected before anything is downloaded.
_PICKLE_SUFFIXES = (".pt", ".pth", ".bin", ".ckpt")

#: Ceiling on an imported head. Heads are small; anything larger is either not a head
#: or an attempt to exhaust memory during the load.
_MAX_HEAD_BYTES = 512 * 1024 * 1024


class InvalidRepoIdError(ValueError):
    """The repo id is not a plain ``owner/name``."""


class PickleRefusedError(ValueError):
    """The repo offers no safetensors. There is no fallback to its pickles."""


def validate_repo_id(repo_id: str) -> str:
    """Return ``repo_id`` if it is a plain ``owner/name``, else raise.

    The ``.``/``..`` segment check is not redundant with the pattern: the pattern bars
    a *leading* dot only, so ``owner/..`` would otherwise satisfy the character class.
    """
    if not _REPO_ID.match(repo_id):
        raise InvalidRepoIdError(
            f"Not a HuggingFace repo id: {repo_id!r}. Expected owner/name."
        )
    if any(part in {".", ".."} for part in repo_id.split("/")):
        raise InvalidRepoIdError(f"Not a HuggingFace repo id: {repo_id!r}")
    return repo_id


def _list_repo_files(repo_id: str) -> list[str]:
    """Files in a HuggingFace repo. Isolated so tests need no network."""
    from huggingface_hub import list_repo_files

    return list(list_repo_files(repo_id))


def _download_repo_file(repo_id: str, filename: str, token: str | None) -> Path:
    """Fetch one file from a repo. Isolated so tests need no network."""
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(repo_id=repo_id, filename=filename, token=token))


def _pick_safetensors(repo_id: str, files: list[str]) -> str:
    """Choose the safetensors weight file, or refuse with the reason."""
    candidates = [name for name in files if name.endswith(".safetensors")]
    if candidates:
        # A plain model.safetensors wins when present; otherwise the first by name, so
        # a sharded repo behaves predictably rather than by listing order.
        if "model.safetensors" in candidates:
            return "model.safetensors"
        return sorted(candidates)[0]

    pickles = sorted(name for name in files if name.endswith(_PICKLE_SUFFIXES))
    if pickles:
        raise PickleRefusedError(
            f"{repo_id} publishes only pickled weights ({', '.join(pickles)}). "
            "This app imports safetensors only — loading a pickle would run arbitrary "
            "code from the repository. Ask the author for a safetensors export."
        )
    raise PickleRefusedError(f"{repo_id} contains no weight file this app can import.")


def _token(settings: Settings) -> str | None:
    secret = settings.hf_token
    return secret.get_secret_value() if secret else None


def import_community_head(
    *,
    repo_id: str,
    head_type_id: str,
    backbone_id: str,
    num_classes: int | None = None,
    name: str | None = None,
    settings: Settings | None = None,
) -> HeadInstance:
    """Import a community head from a HuggingFace repo id. Safetensors only."""
    settings = settings or get_settings()

    validate_repo_id(repo_id)
    spec = require_spec(head_type_id)
    # Backbone first: it is a purely local check, so failing it early means an invalid
    # request never causes a network call on the user's behalf.
    capabilities = read_capabilities(backbone_id)
    require_compatible(spec, capabilities)

    filename = _pick_safetensors(repo_id, _list_repo_files(repo_id))
    local = _download_repo_file(repo_id, filename, _token(settings))

    size = local.stat().st_size
    if size > _MAX_HEAD_BYTES:
        raise IncompatibleHeadError(
            f"{repo_id}/{filename} is {size} bytes, over the {_MAX_HEAD_BYTES} limit "
            "for a head. This does not look like a head checkpoint."
        )

    from safetensors.torch import load_file

    weights: dict[str, Tensor] = load_file(str(local))
    # Digest computed from the bytes that actually arrived — never one the repo claims.
    digest = hashlib.sha256(local.read_bytes()).hexdigest()

    logger.info("Importing community head from %s (%s)", repo_id, filename)
    return register_head(
        spec=spec,
        capabilities=capabilities,
        weights=weights,
        num_classes=num_classes,
        kind="community",
        name=name or repo_id,
        source_repo=repo_id,
        source_digest=digest,
        settings=settings,
    )
