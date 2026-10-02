"""Provider errors in plain words (doc 147), never echoing a request's credentials."""

from __future__ import annotations

import re

from obstore import exceptions as store_errors

#: Anything that looks like a key or token in a provider's message is blanked out.
_SECRET_LIKE = re.compile(r"(?i)(signature|credential|sig|key|token|authorization)=[^&\s\"']+")


class CloudError(ValueError):
    """A store refused or could not be reached; its message is safe to show."""


class CloudConflict(CloudError):
    """A conditional write found a newer version than the one expected (doc 150)."""


def _clean(text: str) -> str:
    return _SECRET_LIKE.sub(r"\1=…", text.splitlines()[0] if text else "")[:300]


def explain(error: Exception, where: str) -> CloudError:
    """What failed, worded for the user, with the provider's first line for the details."""
    detail = _clean(str(error))
    if isinstance(error, store_errors.UnauthenticatedError):
        return CloudError(
            f"The credentials were refused for {where}. Check the key and secret. ({detail})"
        )
    if isinstance(error, store_errors.PermissionDeniedError):
        return CloudError(f"The credentials work but may not read {where}. ({detail})")
    missing = ("NoSuchBucket", "ContainerNotFound", "The specified bucket does not exist")
    if isinstance(error, (store_errors.NotFoundError, FileNotFoundError)) or any(
        code in str(error) for code in missing
    ):
        return CloudError(f"{where} does not exist, or this account cannot see it. ({detail})")
    if isinstance(error, (store_errors.PreconditionError, store_errors.AlreadyExistsError)):
        return CloudConflict(f"{where} changed since it was last read. ({detail})")
    lowered = detail.lower()
    if any(
        word in lowered
        for word in (
            "dns",
            "resolve",
            "connection refused",
            "connect error",
            "error sending request",
            "timed out",
        )
    ):
        return CloudError(
            f"The storage could not be reached. Check the endpoint and the network. ({detail})"
        )
    if (
        "region" in lowered
        or "permanentredirect" in lowered
        or "authorizationheadermalformed" in lowered
    ):
        return CloudError(f"{where} is in another region than the connection says. ({detail})")
    return CloudError(f"The storage refused the request for {where}. ({detail})")
