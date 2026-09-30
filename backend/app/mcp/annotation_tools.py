"""Annotating for SAM 3 and keeping it consistent, for an assistant (doc 110).

The same phrases, checks, target matrix and guideline the Studio shows (docs 103–109), so
an assistant preparing a SAM 3 dataset is told what a person is told.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from app.mcp import client


def register(mcp: MCPServer) -> None:
    """Attach the annotation tools. Called by `server.build`."""

    @mcp.tool()
    async def get_annotation_targets() -> Any:
        """What a dataset can be annotated for, and which layers each model needs.

        For each target (keep all options open, classifier, detector, SAM 2, SAM 3): every
        layer — one class per picture, boxes, outlines, phrases, checked per picture — as
        required, recommended or optional, with the reason. Relay the reasons; recommend
        "keep all options open" when the user is unsure.
        """
        return await client.call("GET", "/annotation-targets")

    @mcp.tool()
    async def list_phrases(dataset_id: str) -> Any:
        """A dataset's SAM 3 phrases: text, class, variations, look-alikes ('confusable'),
        outlines answering to each, and how many pictures were checked 'complete' / 'absent'.
        Every class is listed as its own phrase."""
        return await client.call("GET", f"/datasets/{dataset_id}/phrases")

    @mcp.tool()
    async def add_phrase(
        dataset_id: str,
        text: str,
        class_name: str | None = None,
        classes: list[str] | None = None,
    ) -> Any:
        """Add a phrase, with comma-separated variations: "signal, railway signal, light
        signal" is one phrase with two variations, stored once and expanded at training.

        Two to four variations are enough — they teach SAM 3 that wording varies; every
        synonym is not needed. A phrase belongs to one class (`class_name`, default: the
        phrase itself). A variation that is already another phrase is refused with both
        named. Adding to an existing phrase merges the new variations.

        `classes` (two or more) makes an umbrella term instead (doc 115): "screw" over m8
        and m9 is answered by every outline of both classes, and nothing is linked per
        outline. Use it for a general name over specific classes; use a variation for
        another wording of one class.
        """
        body: dict[str, Any] = {"text": text}
        if class_name:
            body["class_name"] = class_name
        if classes:
            body["classes"] = classes
        return await client.call("POST", f"/datasets/{dataset_id}/phrases", json=body)

    @mcp.tool()
    async def set_phrase_status(
        dataset_id: str,
        path: str,
        phrase: str,
        status: Literal["complete", "absent"] | None,
    ) -> Any:
        """Mark a picture for a phrase: `complete` (every instance of it here has an
        outline), `absent` (none here — a confirmed negative), or null to clear.

        Only checked pictures teach SAM 3: an unchecked picture is left out for that phrase,
        never guessed. Mark `complete` only when every instance really is outlined, and
        `absent` only when you or the user looked — a wrong 'absent' teaches the model to
        miss the object. Pictures where something similar is present are the most valuable
        `absent`s (hard negatives).
        """
        return await client.call(
            "PUT",
            f"/datasets/{dataset_id}/images/phrase-status",
            json={"path": path, "phrase": phrase, "status": status},
        )

    @mcp.tool()
    async def get_annotation_guideline(dataset_id: str) -> Any:
        """The dataset's written annotation conventions. Read it before annotating or
        judging annotations, and follow it; if it is empty, offer to write one with the
        user."""
        return await client.call("GET", f"/datasets/{dataset_id}/guideline")

    @mcp.tool()
    async def set_annotation_guideline(dataset_id: str, text: str) -> Any:
        """Replace the guideline (up to 20,000 characters). Write conventions a second
        annotator can follow: what counts as part of an object, when to mark unclear,
        which name is right. Agree the text with the user before saving it."""
        return await client.call("PUT", f"/datasets/{dataset_id}/guideline", json={"text": text})


__all__ = ["register"]
