"""The guide's "annotate for SAM 3" recipe (docs 103–110), apart from `workflows.py` for its
size."""

from __future__ import annotations

ANNOTATE_FOR = """## 2d. Annotate for the model you will train — SAM 3 above all

Decide what the dataset will train, because the layers differ:
`GET /annotation-targets` (MCP `get_annotation_targets`) lists every target with each layer
as required, recommended or optional, and why. When the user is unsure, recommend
**keep all options open**: boxes, outlines from them in one click, class names as phrases.

**Read the guideline first.** `GET /datasets/{id}/guideline` (MCP
`get_annotation_guideline`) holds the dataset's conventions — what counts as part of an
object, when to mark unclear. Follow it; if it is empty, offer to write one with the user
(`set_annotation_guideline`). Inconsistency between pictures costs more than noise.

**SAM 3 needs three things per picture:**

1. **Outlines** of every instance of a phrase (masks; `POST /segment/boxes` makes them from
   boxes with SAM 2, `POST /segment/refine` corrects one with ⊕/⊖ clicks).
2. **Phrases** — what you would type to find it. `POST /datasets/{id}/phrases` with
   `{"text": "signal, railway signal, light signal", "class_name": "signal"}` is one phrase
   with two variations. **Two to four variations are enough**; the model generalises from
   there. Look-alikes go in `confusable` (`PATCH .../phrases/{id}`), e.g. "street lamp" for
   "signal" — only names of things that rarely share a picture with the phrase. Two things
   that should both be found are two classes, each outlined. A wrong proposal in the same
   picture (a flame's reflection) is rejected, and the picture marked `complete`: the true
   outlines are then the whole answer, and no class is needed for the reflection.
3. **A check per picture and phrase.** `PUT /datasets/{id}/images/phrase-status`
   `{"path": ..., "phrase": "signal", "status": "complete" | "absent" | null}` (MCP
   `set_phrase_status`). `complete`: every instance here is outlined. `absent`: none here —
   a confirmed negative. **Only checked pictures teach**: once any check exists, an
   unchecked picture is left out for that phrase, because an instance nobody outlined yet is
   not "none here".

**Hard negatives** are what makes SAM 3 precise:
- pictures marked `absent` — best where something similar is present;
- look-alikes (`confusable`), asked on pictures marked `complete` that have no rejected
  outline of the phrase;
- rejected outlines: a picture where the model's outline for a phrase was rejected and
  none accepted teaches "not here";
- generic unrelated phrases (`num_negatives`, default 3) and your other phrases
  (`num_cross_negatives`, default 2), added by training — see
  `GET /training/parameters/sam3`.

An *unclear* outline is never used as a negative for its phrase. Before fine-tuning, audit
for `sam3` (section 2c): it reports thin phrases, unchecked pictures, phrases without
variations, and outlines in pieces or twice.
"""
