"""The human-facing files of an export bundle (doc 121): README, predict.py, requirements."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

#: What the runtime imports, pinned to what this app runs so the numbers match.
RUNTIME_PACKAGES = ("torch", "torchvision", "transformers", "safetensors", "pillow", "numpy")

PREDICT_PY = '''"""Run the exported model on one picture.

    python predict.py picture.jpg [--threshold 0.3]

Prints what the app's Inference Viewer shows, as JSON in the picture's own pixels. For
masks and depth it also writes <picture>.mask.png / <picture>.depth.png.
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from PIL import Image

from dino_runtime import Model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("picture")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    model = Model.load(Path(__file__).parent, device=args.device)
    result = model.predict(Image.open(args.picture).convert("RGB"), args.threshold)
    for key, suffix in (("mask_png", ".mask.png"), ("depth_png", ".depth.png")):
        if key in result:
            Path(args.picture + suffix).write_bytes(base64.b64decode(result.pop(key)))
            result[key] = args.picture + suffix
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
'''


def requirements() -> str:
    lines = []
    for package in RUNTIME_PACKAGES:
        try:
            lines.append(f"{package}=={version(package)}")
        except PackageNotFoundError:
            lines.append(package)
    return "\n".join(lines) + "\n"


def _licence(card: dict[str, Any]) -> str:
    base = card.get("base", {})
    terms = base.get("licence", "see the base model's page")
    note = " It may not be used commercially." if base.get("non_commercial") else ""
    return f"The weights build on {base.get('repo_id', base.get('id'))}, licensed {terms}.{note}"


def head_readme(card: dict[str, Any], runnable: bool) -> str:
    classes = ", ".join(card["classes"]) or "(none: this head predicts depth)"
    run = (
        "```bash\npip install -r requirements.txt\npython predict.py picture.jpg\n```\n\n"
        "From code:\n\n```python\nfrom PIL import Image\nfrom dino_runtime import Model\n\n"
        'model = Model.load("path/to/this/folder")\n'
        'picture = Image.open("picture.jpg").convert("RGB")\n'
        "result = model.predict(picture, score_threshold=0.3)\n```\n\n"
        "The first run downloads the base model from HuggingFace "
        f"(`{card['base'].get('repo_id')}`).\n"
        if runnable
        else "This head type is not covered by the exported runtime yet: use `model.json` and "
        "the weights with the app, or build the head from its card.\n"
    )
    return (
        f"# {card['model']['name']}\n\n"
        f"A {card['task']} head ({card['head']['title']}) on the frozen backbone "
        f"`{card['base'].get('repo_id')}`, exported from DinoTraining "
        f"{card['model']['app_version']}.\n\n"
        f"**Classes** (output index order): {classes}\n\n"
        f"## Run it\n\n{run}\n"
        "## What the files are\n\n"
        "- `model.json` — the model card: base model, classes, the exact preprocessing, how "
        "outputs are decoded, metrics, training data and recipe.\n"
        "- `head.safetensors` — the head's weights.\n"
        "- `dino_runtime.py` — the app's own preprocessing, head and decoding code.\n"
        "- `predict.py` — a command-line example.\n"
        "- `model.onnx` — when present: backbone and head as one ONNX graph (see the card's "
        "`onnx` section).\n\n"
        f"## Outputs\n\n{card['outputs']['decode']}\n\n"
        f"## Licence\n\n{_licence(card)}\n"
    )


def finetuned_readme(card: dict[str, Any]) -> str:
    files = ", ".join(f"`{w['file']}`" for w in card["weights"])
    return (
        f"# {card['model']['name']}\n\n"
        f"A fine-tuned `{card['base'].get('repo_id')}` ({card['weights_kind']}), exported from "
        f"DinoTraining {card['model']['app_version']}.\n\n"
        f"**Files:** `model.json` (the card) and {files}.\n\n"
        "These weights replace the matching part of the base model "
        f"(`{card['weights_kind']}`). They run in DinoTraining; to use them elsewhere, load "
        "the base model with `transformers` and load these weights into that part. "
        "`model.json` lists the classes, metrics (with the base model's `baseline` on the same "
        "pictures), training data and settings.\n\n"
        f"## Licence\n\n{_licence(card)}\n"
    )


__all__ = ["PREDICT_PY", "finetuned_readme", "head_readme", "requirements"]
