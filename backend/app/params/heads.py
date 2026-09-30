"""The DINO head's parameters (doc 99). Defaults are `TrainingConfig`'s; a test pins that."""

from __future__ import annotations

from app.params.spec import Choice, Parameter, ParameterSet

EPOCHS = Parameter(
    key="epochs",
    label="Rounds",
    term="epochs",
    help="How many times training goes through all training pictures. More rounds learn "
    "more, until the model starts memorising; the best round is kept either way.",
    default=20,
    why="A head on a frozen backbone learns fast; 20 rounds is enough for a few hundred "
    "pictures, and early stopping ends sooner when nothing improves.",
    kind="int",
    minimum=1,
    maximum=1000,
)

LEARNING_RATE = Parameter(
    key="learning_rate",
    label="Learning speed",
    term="learning rate",
    help="How big each correction step is. Too high and training jumps around or "
    "diverges; too low and it barely moves in the rounds you give it.",
    default=1e-3,
    why="A small head on fixed features tolerates a high rate; 0.001 converges in a "
    "handful of rounds.",
    kind="float",
    minimum=1e-6,
    maximum=1.0,
)

BATCH_SIZE = Parameter(
    key="batch_size",
    label="Pictures per step",
    term="batch size",
    help="How many pictures are looked at before the model is corrected once. More "
    "pictures per step give calmer, averaged corrections but fewer of them per round.",
    default=1,
    why="One picture per step is how every head so far was trained, and it suits small "
    "datasets: more corrections per round. Try 4–8 if the loss curve is very jumpy.",
    kind="int",
    minimum=1,
    maximum=64,
)

PATIENCE = Parameter(
    key="early_stopping_patience",
    label="Patience",
    term="early stopping",
    help="Training stops when the validation score has not improved for this many "
    "rounds in a row. It saves time once the model has learned what it can.",
    default=5,
    why="Five rounds lets a noisy score recover from a dip without running on for long "
    "after the model has stopped improving.",
    kind="int",
    minimum=1,
    maximum=100,
)

WEIGHT_DECAY = Parameter(
    key="weight_decay",
    label="Weight shrinkage",
    term="weight decay",
    help="Gently pulls the model's numbers towards zero, which discourages memorising "
    "individual pictures. Higher values mean a simpler, more cautious model.",
    default=0.01,
    why="0.01 is the usual AdamW setting: enough to curb memorising without holding back learning.",
    kind="float",
    level="advanced",
    minimum=0.0,
    maximum=1.0,
)

SCHEDULE = Parameter(
    key="lr_schedule",
    label="Speed schedule",
    term="learning-rate schedule",
    help="Whether the learning speed stays the same every round, or slows down along a "
    "cosine curve towards the end so the last rounds make only fine adjustments.",
    default="constant",
    why="Constant is how every head so far was trained. Cosine often helps longer runs "
    "(30+ rounds) settle.",
    kind="choice",
    level="advanced",
    choices=(Choice("constant", "Constant"), Choice("cosine", "Slow down (cosine)")),
)

WARMUP = Parameter(
    key="warmup_epochs",
    label="Warm-up rounds",
    term="warm-up",
    help="The first rounds start at a fraction of the learning speed and ramp up to it, "
    "so a model that has not seen your data yet is not jolted by big early steps.",
    default=0,
    why="A head starts from scratch on stable features and does not need it; 1–2 rounds "
    "help when the loss spikes at the start.",
    kind="int",
    level="advanced",
    minimum=0,
    maximum=50,
)

SEED = Parameter(
    key="split_seed",
    label="Random seed",
    term="seed",
    help="Fixes the random choices (split, order), so the same settings give the same "
    "result again. Change it to see how much a result depends on luck.",
    default=42,
    why="Any fixed number works; 42 is a convention. A recipe's split has its own seed.",
    kind="int",
    level="advanced",
    minimum=0,
    maximum=2**31 - 1,
    recipe_overrides=True,
)

VAL_FRACTION = Parameter(
    key="val_fraction",
    label="Validation share",
    term="validation fraction",
    help="The share of pictures held back to pick the best round and to stop early. They "
    "are not trained on.",
    default=0.2,
    why="A fifth is enough to judge a round on small datasets while leaving most pictures "
    "for training. A recipe's split replaces it.",
    kind="float",
    level="advanced",
    minimum=0.0,
    maximum=0.5,
    recipe_overrides=True,
)

TEST_FRACTION = Parameter(
    key="test_fraction",
    label="Test share",
    term="test fraction",
    help="The share of pictures kept out of everything until the end, for an honest final "
    "score. 0 means no test score.",
    default=0.1,
    why="A tenth gives a final check without starving training. A recipe's split replaces it.",
    kind="float",
    level="advanced",
    minimum=0.0,
    maximum=0.5,
    recipe_overrides=True,
)

HEAD = ParameterSet(
    family="head",
    title="DINO head",
    covers="Every head trained on a frozen DINOv2/DINOv3 backbone",
    parameters=(
        EPOCHS,
        LEARNING_RATE,
        BATCH_SIZE,
        PATIENCE,
        WEIGHT_DECAY,
        SCHEDULE,
        WARMUP,
        SEED,
        VAL_FRACTION,
        TEST_FRACTION,
    ),
)

__all__ = ["HEAD"]
