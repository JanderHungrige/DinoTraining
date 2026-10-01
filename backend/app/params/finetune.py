"""Fine-tuning parameters shared by every family, plus RF-DETR and DINO backbones (doc 99).

Every default is the value the adapter used as a constant before it became a setting, so
moving it here changed no result.
"""

from __future__ import annotations

from app.params.spec import Parameter, ParameterSet


def rounds(default: int, why: str) -> Parameter:
    return Parameter(
        key="epochs",
        label="Rounds",
        term="epochs",
        help="How many times training goes through all training pictures. The original "
        "model competes as round 0 and the best round is kept, so more rounds cost time, "
        "never quality.",
        default=default,
        why=why,
        kind="int",
        minimum=1,
        maximum=200,
    )


def learning_rate(default: float, why: str) -> Parameter:
    return Parameter(
        key="learning_rate",
        label="Learning speed",
        term="learning rate",
        help="How big each correction step is. A pretrained model is being adjusted, not "
        "taught from scratch: too high a speed destroys what it already knows.",
        default=default,
        why=why,
        kind="float",
        minimum=1e-7,
        maximum=1e-2,
    )


def weight_decay(default: float) -> Parameter:
    return Parameter(
        key="weight_decay",
        label="Weight shrinkage",
        term="weight decay",
        help="Gently pulls the trained numbers towards zero, which discourages memorising "
        "individual pictures.",
        default=default,
        why="The value this model's training used before it became a setting.",
        kind="float",
        level="advanced",
        minimum=0.0,
        maximum=0.5,
    )


SEED = Parameter(
    key="seed",
    label="Random seed",
    term="seed",
    help="Fixes the random choices (order, jitter), so the same settings give the same "
    "result again. Change it to see how much a result depends on luck.",
    default=42,
    why="Any fixed number works; 42 is a convention.",
    kind="int",
    level="advanced",
    minimum=0,
    maximum=2**31 - 1,
)


def cache_share(default: float) -> Parameter:
    return Parameter(
        key="cache_share",
        label="Memory for cached pictures",
        term="feature-cache share",
        help="The share of this computer's memory used to keep each picture's encoded "
        "version between rounds. More is faster; too much makes the whole computer slow.",
        default=default,
        why="Measured on a 16 GB Mac: a fixed 3 GB cache beside the model pushed it into "
        "heavy swapping, so the cache is a share of memory instead.",
        kind="float",
        level="advanced",
        minimum=0.0,
        maximum=0.5,
    )


def unfreeze(default: int, level: str, why: str, minimum: int) -> Parameter:
    return Parameter(
        key="unfreeze_blocks",
        label="Backbone blocks to train",
        term="unfreeze",
        help="How many of the backbone's last layers are adjusted too. The last layers "
        "hold the most task-specific knowledge; more layers can adapt further but need "
        "more pictures and memory.",
        default=default,
        why=why,
        kind="int",
        level="basic" if level == "basic" else "advanced",
        minimum=minimum,
        maximum=24,
    )


RF_DETR = ParameterSet(
    family="rf-detr",
    title="RF-DETR",
    covers="rf-detr-nano, rf-detr-small, rf-detr-base",
    parameters=(
        rounds(
            10,
            "Detectors keep improving over many rounds; 10 balances time and quality on a laptop.",
        ),
        learning_rate(
            1e-4,
            "The usual DETR fine-tuning rate: fast enough to learn new "
            "classes, slow enough to keep what the model knows.",
        ),
        Parameter(
            key="batch_size",
            label="Pictures per step",
            term="gradient accumulation",
            help="How many pictures are looked at before the model is corrected once. "
            "More give calmer corrections but fewer of them per round.",
            default=1,
            why="One picture per step is how RF-DETR was fine-tuned here so far (0.62 test "
            "mAP on Blood cells). Try 4 if the loss is very jumpy.",
            kind="int",
            minimum=1,
            maximum=32,
        ),
        weight_decay(1e-4),
        Parameter(
            key="max_grad_norm",
            label="Gradient limit",
            term="gradient clipping",
            help="Caps how strong a single correction may be. It protects the model from "
            "one bad picture or a loss spike undoing what it learned.",
            default=0.1,
            why="DETR losses spike in the first steps after the classifier is re-opened "
            "for your classes; 0.1 is the value RF-DETR's own training uses.",
            kind="float",
            level="advanced",
            minimum=0.001,
            maximum=100.0,
        ),
        unfreeze(
            0,
            "advanced",
            "0 trains the detector's own layers only, which is what "
            "RF-DETR's fine-tuning does and needs the fewest pictures.",
            0,
        ),
        SEED,
    ),
)

BACKBONE = ParameterSet(
    family="dino-backbone",
    title="DINO backbone",
    covers="dinov2-*/dinov3-* with a classification or segmentation head",
    parameters=(
        rounds(
            6,
            "The backbone is only nudged; six rounds measured a gain on the "
            "filled-ring set (0.849 → 0.869) without overfitting.",
        ),
        learning_rate(
            1e-3,
            "This is the head's speed; the backbone gets a fraction of it "
            "(see Backbone speed factor).",
        ),
        unfreeze(
            4,
            "basic",
            "The last four blocks carry the most task-specific features; "
            "more needs more pictures than most datasets have.",
            1,
        ),
        Parameter(
            key="backbone_lr_scale",
            label="Backbone speed factor",
            term="backbone learning-rate scale",
            help="The backbone learns at this fraction of the head's speed. A backbone that "
            "already works is being nudged; at full speed a few hundred pictures destroy it.",
            default=0.1,
            why="A tenth keeps the pretrained features while letting them adapt.",
            kind="float",
            level="advanced",
            minimum=0.001,
            maximum=1.0,
        ),
        weight_decay(0.01),
        SEED,
    ),
)

__all__ = ["BACKBONE", "RF_DETR", "SEED", "cache_share", "learning_rate", "rounds", "weight_decay"]
