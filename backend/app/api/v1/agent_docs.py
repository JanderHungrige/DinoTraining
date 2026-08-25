"""The API guide, as one document an assistant can be handed (doc 63).

The API was already complete for the workflows people want to automate, and already
machine-described — 51 paths at `/openapi.json`, with Swagger UI at `/docs`. What was
missing is the **order**: a schema says `POST /foundation/finetune` exists and what its body
looks like, and cannot say that the model must be installed first, that installing is a job
you poll, or that `image_path` is a path on this machine.

So this route joins two halves that are deliberately produced differently: hand-written
recipes for the order, and a reference generated from the live schema for the surface. The
generated half cannot go stale; the written half encodes decisions no schema records.

**One document, not one per workflow.** The caller is pasting it into a context window, and
five fetches to assemble one prompt is five ways to send half of it.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Query, Request, Response

from app.docs.reference import render_reference
from app.docs.workflows import WORKED_EXAMPLE, WORKFLOWS

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/docs/agent-guide",
    summary="The whole API as one document, for an AI assistant to follow",
    response_class=Response,
    responses={200: {"content": {"text/markdown": {}}, "description": "The guide."}},
)
async def agent_guide(
    request: Request,
    format: Literal["md"] = Query(
        default="md",
        description=(
            "Markdown only, and deliberately: it is what these models read best, and a "
            "PDF is produced by the app's own print view rather than here."
        ),
    ),
) -> Response:
    """Compose the guide and hand it back as markdown.

    `request.app.openapi()` rather than a stored copy: it is the schema of the process
    answering the call, so a guide fetched from a running backend describes that backend.
    """
    document = build_guide(request.app.openapi())
    logger.info("Served the agent guide (%d characters)", len(document))
    return Response(
        content=document,
        media_type="text/markdown; charset=utf-8",
        # Named so a browser "save as" and the app's download button agree on the filename.
        headers={"Content-Disposition": 'inline; filename="dinotraining-api-guide.md"'},
    )


def build_guide(openapi: dict[str, object]) -> str:
    """Recipes, then a worked example, then the generated reference.

    That order is the reading order for the audience. An assistant given the endpoint list
    first will start calling things; given the recipes first it has the preconditions before
    it has the URLs, which is the difference between following a workflow and guessing one.
    """
    sections = [*WORKFLOWS, WORKED_EXAMPLE, render_reference(openapi)]
    return "\n\n".join(section.strip() for section in sections) + "\n"


__all__ = ["agent_guide", "build_guide"]
