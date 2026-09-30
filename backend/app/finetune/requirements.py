"""What each fine-tunable model needs its training data to look like (doc 92).

Jan's point for Wave 12: *what matters most is telling the user and the assistant exactly
what form the training data has to take for each model.* So this is the one source. The
Training tab renders it as a requirements card, the API and MCP return it as data, and
`preflight.py` checks a dataset against it and refuses in plain language before a job
starts.

Every number here is a floor below which fine-tuning is not worth the time, not a
guarantee above it. They are stated with their reason, because a user told only "50" will
reasonably ask "why not 20".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

AnnotationKind = Literal["boxes", "instance-masks", "phrase-masks", "image-labels"]
PromptKind = Literal["none", "box-from-mask", "noun-phrase"]


class FinetuneRequirements(BaseModel):
    id: str
    #: The catalogue model that is fine-tuned (doc 02).
    model_id: str
    label: str
    task: str
    annotation_kind: AnnotationKind
    prompt_kind: PromptKind
    min_images: int
    min_instances_per_class: int
    #: Why those minimums, in one sentence.
    minimums_why: str
    image_sizes: str
    #: A Wave 11 recipe must be given: its leak-free split is what the base-vs-fine-tuned
    #: comparison is measured on.
    recipe_required: bool
    #: HuggingFace gating, licence approval, memory: what must be true of the machine.
    gates: list[str]
    #: What the training data must look like, for a person and for an assistant.
    data_format: str
    #: What training changes, and what it leaves alone.
    what_trains: str
    #: False until this model's training adapter exists; the reason says what is missing.
    available: bool = True
    unavailable_reason: str = ""


_MASKS_FORMAT = (
    "One mask per object, per image: an outline of exactly that object, stored as an "
    "annotation with its class name. Boxes alone are not enough; the model learns outlines "
    "from outlines. Make masks in the Annotation Studio or the Dataset Generator with "
    "Grounded SAM, then correct them. Reject wrong masks rather than deleting them: a "
    "rejected mask teaches 'not this'. Every image must be segmented completely for the "
    "classes you train, because an object left without a mask is taught as background."
)

REQUIREMENTS: tuple[FinetuneRequirements, ...] = (
    FinetuneRequirements(
        id="rf-detr-nano",
        model_id="rf-detr-nano",
        label="RF-DETR (nano)",
        task="detection",
        annotation_kind="boxes",
        prompt_kind="none",
        min_images=30,
        min_instances_per_class=20,
        minimums_why="RF-DETR starts from COCO detection and adapts in a few epochs, so "
        "it needs far less than a head trained from scratch, but not nothing.",
        image_sizes="Any size; resized (stretched) to 384 px. Small objects need tiles "
        "(see Prepare data → What the model sees).",
        recipe_required=False,
        gates=[],
        data_format="One box per object: a tight rectangle around each object, with its "
        "class name. Every object of a trained class in every image must be boxed, or the "
        "missing ones are taught as background. Mark boxes you are unsure of 'unclear'.",
        what_trains="The projector and the detection decoder; the DINOv2 backbone stays "
        "frozen unless you unfreeze its last blocks.",
    ),
    FinetuneRequirements(
        id="sam2.1-hiera-small",
        model_id="sam2.1-hiera-small",
        label="SAM 2.1 (small)",
        task="segmentation",
        annotation_kind="instance-masks",
        prompt_kind="box-from-mask",
        min_images=20,
        min_instances_per_class=50,
        minimums_why="SAM already segments almost anything; fine-tuning teaches it where "
        "your objects' edges are. Fifty outlines per class show it enough of them.",
        image_sizes="Any size; resized (stretched) to 1024 px. Outlines are learned at "
        "256 px, so detail finer than about 4 input pixels cannot improve.",
        recipe_required=True,
        gates=[],
        data_format=_MASKS_FORMAT + " The prompt for each mask is made from the mask "
        "itself (its box, jittered), so you do not provide prompts.",
        what_trains="The mask decoder only. The image encoder stays frozen, which keeps it "
        "fast and saves the result in a few megabytes.",
    ),
    FinetuneRequirements(
        id="sam3",
        model_id="sam3",
        label="SAM 3",
        task="concept-segmentation",
        annotation_kind="phrase-masks",
        prompt_kind="noun-phrase",
        min_images=30,
        min_instances_per_class=50,
        minimums_why="SAM 3 finds every instance of a phrase; it needs enough images per "
        "phrase to learn both what the phrase means here and where its edges are.",
        image_sizes="Any size; resized to 1008 px.",
        recipe_required=True,
        gates=[
            "Gated on HuggingFace: Meta approves access by hand.",
            "About 3.2 GB of weights; training needs roughly 16 GB of memory.",
        ],
        data_format=_MASKS_FORMAT + " The class name is the noun phrase SAM 3 is prompted "
        "with, so name classes the way you would ask for them ('rail signal', not "
        "'class_3'). Images where a phrase has no instance are useful: they teach 'none "
        "here'.",
        what_trains="The detection and mask decoders and the scoring head (15 M of 840 M "
        "parameters); the image and text encoders stay frozen. About 6 s per picture the "
        "first round on an M1, then about 1 s.",
    ),
    *(
        FinetuneRequirements(
            id=f"{backbone}-{task}",
            model_id=backbone,
            label=f"{'DINOv2' if backbone.startswith('dinov2') else 'DINOv3'} {size} — {task}",
            task=task,
            annotation_kind="image-labels" if task == "classification" else "instance-masks",
            prompt_kind="none",
            min_images=100 if task == "classification" else 30,
            min_instances_per_class=30,
            minimums_why="Unfreezing part of a backbone changes features every other "
            "head relies on; with less data it forgets more than it learns.",
            image_sizes="Any size; letterboxed to 448 px (224 for classification).",
            recipe_required=True,
            gates=[]
            if backbone.startswith("dinov2")
            else ["Gated on HuggingFace: accept the DINOv3 licence and set a token."],
            data_format=(
                "One class per image: each image has boxes of exactly one class (the "
                "class of the image). Images with several classes are skipped."
                if task == "classification"
                else _MASKS_FORMAT
            ),
            what_trains="The last blocks of the backbone together with a task head, saved "
            "as a new backbone variant with its own id. Heads trained on the original "
            "backbone never run on the variant.",
        )
        for backbone, size in (
            ("dinov2-small", "ViT-S/14"),
            ("dinov3-vitb16", "ViT-B/16"),
            ("dinov3-vitl16", "ViT-L/16"),
        )
        for task in ("classification", "segmentation")
    ),
)

_BY_ID = {spec.id: spec for spec in REQUIREMENTS}


def get_requirements(finetune_id: str) -> FinetuneRequirements:
    spec = _BY_ID.get(finetune_id)
    if spec is None:
        raise LookupError(f"No fine-tunable model {finetune_id}")
    return spec


__all__ = ["REQUIREMENTS", "FinetuneRequirements", "get_requirements"]
