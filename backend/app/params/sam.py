"""SAM 2.1 and SAM 3 fine-tuning parameters (doc 99): loss weights, jitter, caches."""

from __future__ import annotations

from app.params.finetune import SEED, cache_share, learning_rate, rounds, weight_decay
from app.params.spec import Parameter, ParameterSet


def loss_weight(key: str, label: str, term: str, help_text: str, default: float) -> Parameter:
    return Parameter(
        key=key,
        label=label,
        term=term,
        help=help_text + " Raising it makes training care more about this than the rest.",
        default=default,
        why="The weight from the model's own published training recipe.",
        kind="float",
        level="advanced",
        minimum=0.0,
        maximum=100.0,
    )


SAM2 = ParameterSet(
    family="sam2",
    title="SAM 2.1",
    covers="sam2.1-hiera-small, sam2.1-hiera-base-plus, sam2.1-hiera-large",
    parameters=(
        rounds(
            6,
            "Only the small mask decoder trains; six rounds took the filled-ring "
            "convention from 0.80 to 0.96 mIoU.",
        ),
        learning_rate(
            1e-4,
            "The rate SAM's decoder tolerates without forgetting how to outline things in general.",
        ),
        weight_decay(1e-4),
        loss_weight(
            "focal_weight",
            "Pixel focus",
            "focal loss",
            "Counts wrong pixels, weighting the hard ones (edges, thin parts) most.",
            20.0,
        ),
        loss_weight(
            "dice_weight",
            "Overlap",
            "dice loss",
            "Rewards the predicted outline covering the true one as a whole.",
            1.0,
        ),
        loss_weight(
            "iou_weight",
            "Self-rating",
            "IoU-head loss",
            "Teaches SAM to rate its own outline honestly, which its score uses.",
            1.0,
        ),
        Parameter(
            key="box_jitter",
            label="Box looseness",
            term="box jitter",
            help="During training each object's box is moved by up to this share of its "
            "size, so the model learns to cope with a loosely drawn box.",
            default=0.1,
            why="A tenth matches how far a hand-drawn or detected box is usually off. 0 "
            "trains on exact boxes only.",
            kind="float",
            level="advanced",
            minimum=0.0,
            maximum=0.5,
        ),
        Parameter(
            key="max_objects",
            label="Objects per step",
            term="objects per image",
            help="A crowded picture is trained on this many of its objects per step, "
            "chosen at random each round, to keep memory in check.",
            default=16,
            why="Sixteen fits a 16 GB Mac comfortably and still covers most pictures fully.",
            kind="int",
            level="advanced",
            minimum=1,
            maximum=128,
        ),
        Parameter(
            key="point_prompts",
            label="Click prompts per object",
            term="point prompts",
            help="In half the training steps each object's box comes with this many clicks "
            "inside it, so the fine-tuned SAM still answers the Studio's ⊕/⊖ clicks. 0 trains "
            "on boxes only.",
            default=1,
            why="One click is what the Studio's outline tool sends first; half the steps keep "
            "box-only prompts as good as before (doc 108).",
            kind="int",
            level="advanced",
            minimum=0,
            maximum=5,
        ),
        cache_share(0.15),
        SEED,
    ),
)

SAM3 = ParameterSet(
    family="sam3",
    title="SAM 3",
    covers="sam3",
    parameters=(
        rounds(
            4,
            "Each round is slow on a laptop (every picture against every phrase); "
            "four rounds is a first result in reasonable time.",
        ),
        learning_rate(
            1e-4, "The rate for the decoders SAM 3 trains here; the large encoders stay frozen."
        ),
        Parameter(
            key="num_negatives",
            label="Generic negatives",
            term="num_negatives",
            help="Per picture and round, this many unrelated everyday phrases (car, person, "
            "dog, …) are asked and must find nothing — so SAM 3 does not answer every phrase "
            "with your objects. Phrases sharing a word with yours are left out. 0 turns it off.",
            default=3,
            why="Two to four works well in published SAM 3 fine-tuning (SAM3_LoRA); each adds "
            "one query per picture, so more also means slower rounds.",
            kind="int",
            minimum=0,
            maximum=10,
        ),
        Parameter(
            key="num_cross_negatives",
            label="Cross negatives",
            term="num_cross_negatives",
            help="Your own phrases known to be absent from a picture ('not in this picture', "
            "or another class) are asked there and must find nothing. With more than 50 "
            "phrases only this many are sampled per picture; below that all are used.",
            default=2,
            why="SAM3_LoRA's default: enough to learn which description is meant, without one "
            "picture turning into hundreds of queries on a large vocabulary.",
            kind="int",
            minimum=0,
            maximum=20,
        ),
        Parameter(
            key="all_variations",
            label="Every wording each round",
            term="all variations",
            help="On: each variation of a phrase is its own query every round (more steps). "
            "Off: one wording is picked at random each round, so all are seen over the rounds.",
            default=False,
            why="Off keeps a round as long as before while every wording is still learnt.",
            kind="bool",
            level="advanced",
        ),
        Parameter(
            key="rejected_as_negatives",
            label="Rejected outlines as negatives",
            term="hard negatives from rejections",
            help="A picture where you rejected the model's outline for a phrase, and accepted "
            "none, teaches 'not here' for that phrase even if it was not checked.",
            default=True,
            why="A rejection is the most specific lesson there is: the model thought it was "
            "there, and it was not.",
            kind="bool",
            level="advanced",
        ),
        weight_decay(1e-4),
        loss_weight(
            "class_weight",
            "Found or not",
            "classification loss",
            "Teaches which of SAM 3's guesses are real objects of the phrase.",
            2.0,
        ),
        loss_weight(
            "l1_weight",
            "Box position",
            "L1 box loss",
            "Pulls each found object's box towards the true box.",
            5.0,
        ),
        loss_weight(
            "giou_weight",
            "Box overlap",
            "GIoU loss",
            "Rewards boxes that overlap the true box well, whatever their size.",
            2.0,
        ),
        loss_weight(
            "mask_weight",
            "Pixel focus",
            "mask focal loss",
            "Counts wrong pixels in each outline, weighting the hard ones most.",
            5.0,
        ),
        loss_weight(
            "dice_weight",
            "Overlap",
            "dice loss",
            "Rewards each outline covering the true one as a whole.",
            5.0,
        ),
        Parameter(
            key="score_threshold",
            label="Evaluation score threshold",
            term="score threshold",
            help="When scoring the model, a guess counts as found only above this "
            "confidence. It changes the reported number, not the training.",
            default=0.5,
            why="0.5 is SAM 3's own default when it is used for annotation in this app.",
            kind="float",
            level="advanced",
            minimum=0.05,
            maximum=0.95,
        ),
        cache_share(0.08),
        SEED,
    ),
)

__all__ = ["SAM2", "SAM3"]
