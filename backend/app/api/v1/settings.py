"""Credentials and licence acknowledgements the user supplies themselves.

The app never downloads gated weights on the user's behalf and never ships a token. What it
does is give them somewhere to put their own, and make the obligations attached to a gated
model visible rather than implied.

**The token goes in and does not come back out.** No handler here returns it, no log line
contains it, and the read endpoint reports only whether one is configured plus a masked
hint. That is a hard rule, not a preference — see `24-hf-token-settings`.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.env_file import env_file_path, mask_secret, read_env, write_env_value
from app.ml.registry import all_models, licence_url

logger = logging.getLogger(__name__)
router = APIRouter()

HF_TOKEN_KEY = "HF_TOKEN"
ACCEPTED_LICENCES_KEY = "DINO_ACCEPTED_LICENCES"

#: Long enough to be a real HuggingFace token rather than a paste accident. Deliberately
#: loose: HF has changed its prefix before, and rejecting a valid token is worse than
#: accepting a wrong one, which fails visibly on the next download anyway.
_MIN_TOKEN_LENGTH = 8


class TokenStatus(BaseModel):
    """What the admin tab may know about the token. Never the token itself."""

    configured: bool
    #: At most the last four characters, so a user can tell which token is stored.
    hint: str | None = None
    #: Absolute path, so the user can find and edit the file by hand if they prefer.
    env_file: str
    accepted_licences: list[str] = Field(default_factory=list)


class SetTokenRequest(BaseModel):
    token: str = Field(min_length=1, description="Your own HuggingFace access token.")


class AcceptLicenceRequest(BaseModel):
    model_id: str = Field(min_length=1)


def _accepted() -> list[str]:
    raw = read_env().get(ACCEPTED_LICENCES_KEY, "")
    return [item for item in (part.strip() for part in raw.split(",")) if item]


def _status() -> TokenStatus:
    secret = get_settings().hf_token
    token = secret.get_secret_value() if secret else None
    return TokenStatus(
        configured=bool(token),
        hint=mask_secret(token),
        env_file=str(env_file_path()),
        accepted_licences=_accepted(),
    )


@router.get(
    "/settings/hf-token",
    response_model=TokenStatus,
    summary="Whether a HuggingFace token is configured (never the token itself)",
)
async def get_token_status() -> TokenStatus:
    return _status()


@router.put(
    "/settings/hf-token",
    response_model=TokenStatus,
    summary="Save your own HuggingFace token to .env",
)
async def set_token(request: SetTokenRequest) -> TokenStatus:
    token = request.token.strip()
    if len(token) < _MIN_TOKEN_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=(
                "That does not look like a HuggingFace access token. "
                "Create one at https://huggingface.co/settings/tokens — a read token is enough."
            ),
        )

    write_env_value(HF_TOKEN_KEY, token)
    # uvicorn does not reload, and the settings object is cached for the process lifetime.
    # Without this the user saves a token and the very next download still reports none.
    get_settings.cache_clear()

    logger.info("HuggingFace token updated by the user")  # never the value
    return _status()


@router.delete(
    "/settings/hf-token",
    response_model=TokenStatus,
    summary="Remove the stored token",
)
async def clear_token() -> TokenStatus:
    write_env_value(HF_TOKEN_KEY, "")
    get_settings.cache_clear()
    logger.info("HuggingFace token cleared by the user")
    return _status()


@router.post(
    "/settings/accepted-licences",
    response_model=TokenStatus,
    summary="Record that the user has read a model's licence",
)
async def accept_licence(request: AcceptLicenceRequest) -> TokenStatus:
    """Record an acknowledgement for one catalogue model.

    This is a record that the user was shown the terms and said they had read them. It is
    not a substitute for accepting them on HuggingFace — that happens on Meta's own page,
    and only Meta can grant access. Storing it here is what lets Wave 8 packaging state
    which custom-licensed models a build has been through.
    """
    known = {spec.id for spec in all_models()}
    if request.model_id not in known:
        raise HTTPException(status_code=404, detail=f"Unknown model: {request.model_id}")

    accepted = _accepted()
    if request.model_id not in accepted:
        accepted.append(request.model_id)
        write_env_value(ACCEPTED_LICENCES_KEY, ",".join(sorted(accepted)))

    logger.info("User acknowledged the licence for %s", request.model_id)
    return _status()


class LicenceNotice(BaseModel):
    model_id: str
    licence: str
    licence_url: str
    requires_access_request: bool
    accepted: bool
    explanation: str


class LicenceNoticeList(BaseModel):
    notices: list[LicenceNotice]


@router.get(
    "/settings/licences",
    response_model=LicenceNoticeList,
    summary="Every model that needs the user to do something before it can be downloaded",
)
async def list_licence_notices() -> LicenceNoticeList:
    """Explanation text lives here, beside the data it describes.

    Putting these sentences in the frontend would let the wording drift away from the
    `requires_access_request` flag that makes them true or false.
    """
    accepted = set(_accepted())
    notices: list[LicenceNotice] = []

    for spec in all_models():
        if not spec.gated:
            continue
        if spec.requires_access_request:
            explanation = (
                f"{spec.repo_id} is published under the {spec.licence} and access is "
                "granted by hand. Two steps, both on HuggingFace and both yours to take: "
                "request access on the model page and accept the licence there, then paste "
                "your own access token below. This app never downloads it for you. Approval "
                "comes from a person, so a valid token can still be refused until it lands."
            )
        else:
            explanation = (
                f"{spec.repo_id} is published under the {spec.licence}. Accept it on the "
                "model page, then paste your own HuggingFace access token below. Access is "
                "immediate once the terms are accepted."
            )
        notices.append(
            LicenceNotice(
                model_id=spec.id,
                licence=spec.licence,
                licence_url=licence_url(spec),
                requires_access_request=spec.requires_access_request,
                accepted=spec.id in accepted,
                explanation=explanation,
            )
        )

    return LicenceNoticeList(notices=notices)
