---
id: dinotraining-wave-12
title: "Wave 12: Fine-Tuning SAM 2, SAM 3 and DINOv3"
initiative: dinotraining
initiative_version: 10
status: planned
depends_on: dinotraining-wave-11
demo_state: "A user picks SAM 2 in Training, sees exactly what training data it needs and whether their prepared dataset meets it, fine-tunes it on their own masks, and sees held-out mIoU improve over the base model. The same works for DINOv3. SAM 3 either fine-tunes or states precisely why it cannot on this machine. An assistant over MCP asks for each model's data requirements and gets the same answer the user sees."
created: 2026-09-29
hash: 6b4e49ce
---

# Wave 12: Fine-Tuning SAM 2, SAM 3 and DINOv3

**Jan's request (2026-09-29):** SAM 2 and SAM 3 should be fine-tunable on your own dataset,
and so should DINOv3 if it is included. It is: `dinov3-vitb16` and `dinov3-vitl16` are in
the catalogue, both gated behind the HF token (doc 24). **What matters most is telling the
user and the MCP exactly what form the training data has to take for each model.**

Planned after Wave 11 on purpose: fine-tuning consumes Wave 11's preparation recipe (split,
input plan, imbalance) rather than inventing a second, weaker version of it.

## What already exists

- **Doc 44: the fine-tune path.** It exists for RF-DETR: a job runner, whole-model
  persistence as a "fine-tuned model", `detection_metrics` for comparability, and cancel.
  This wave generalises it, and does not start again.
- **Doc 55: unfreezing.** A head cannot carry a backbone: modifying one inside a
  `HeadInstance` is discarded (0.000 mAP in a fresh process). **Unfreezing belongs on the
  fine-tune path, which saves the whole model.** DINOv3 fine-tuning is exactly that, and
  CLAUDE.md's "backbones are frozen" stays true of the *head* path.
- **Masks are stored per annotation** (docs 22 and 61) with COCO RLE, which is SAM 2's
  training target.

## Demo-State

1. **SAM 2.1.** In Training the user picks "Fine-tune SAM 2.1 (small)".
   - **A requirements card:** instance masks (not just boxes), with a prompt per mask
     derived from the mask's box, ≥ 50 masks per class, images of any size, split from the
     recipe.
   - **Readiness:** the card says their prepared dataset passes, or which rule it breaks
     and how to fix it.
   - **After fine-tuning:** held-out mIoU of the base vs the fine-tuned model on the same
     split, plus example overlays.
   - **Selectable everywhere:** the fine-tuned model appears in the Grounded SAM tiers, the
     Studio and the Inference Viewer.
2. **DINOv3** does the same for a classification or segmentation task, saved as a fine-tuned
   backbone variant with its task head.
3. **SAM 3** either completes the same flow, or refuses up front with the concrete reason:
   VRAM or unified memory needed vs available, the gated licence, or no trainable path in
   the installed library. It points at Wave 13's remote runner.
4. **MCP.** The assistant asks for SAM 2's requirements and gets the same card as data. A
   fine-tune started over MCP with a dataset that breaks a rule is refused with the same
   explanation.

*(Not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | data-requirements-contract | — | planned | — |
| 2 | finetune-framework | — | planned | data-requirements-contract |
| 3 | sam2-finetune | — | planned | finetune-framework |
| 4 | dinov3-finetune | — | planned | finetune-framework |
| 5 | sam3-finetune | — | planned | sam2-finetune |
| 6 | finetune-ui | — | planned | sam2-finetune, dinov3-finetune |
| 7 | finetune-for-agents | — | planned | data-requirements-contract, finetune-framework |

### Feature notes

1. **data-requirements-contract.** One machine-readable spec per fine-tunable model. It
   records:
   - the task;
   - the annotation kind (boxes, instance masks, or phrase + mask);
   - the prompt kind;
   - the minimum images and instances per class;
   - accepted image sizes;
   - whether a Wave 11 recipe is required;
   - the licence gates.

   **One source rendered three ways:**
   - the UI's requirements card;
   - the API and MCP descriptions (docs 63 and 64);
   - a **preflight check** that refuses in plain language, naming the rule, the numbers and
     the fix, before a job starts.

   RF-DETR (doc 44) gets its spec too, so the whole fine-tune family speaks the same way.
2. **finetune-framework.** Doc 44's runner is generalised behind per-model adapters:
   - data → targets, the loss, the eval metric, save and load;
   - one job lifecycle (progress, cancel, metrics stream per doc 13);
   - base-vs-fine-tuned evaluation on the recipe's held-out split, always;
   - saved as a "fine-tuned model" with full provenance: base model, recipe, dataset and
     metrics.
3. **sam2-finetune.**
   - **What trains:** the mask decoder, with the prompt encoder optional; the image encoder
     stays frozen, as the default and cheap path.
   - **Prompts** are sampled from the ground-truth masks (box plus jittered points) for each
     instance.
   - **Loss:** focal + dice, and IoU-head regression as SAM's own training does.
   - **Evaluated** by mIoU on held-out instances.
   - **Registered** as a SAM 2.1 variant, so the Grounded SAM tiers (doc 27) can use a
     fine-tuned segmenter half.
4. **dinov3-finetune.** The doc 55 machinery on the fine-tune path:
   - the last N blocks are unfrozen, and a task head (classification or segmentation) is
     trained with it;
   - the whole model is saved as a *fine-tuned backbone variant* with its own id.
   - **Feature caches and heads are keyed by backbone id**, so heads trained on the base can
     never be silently composed with the variant, or the reverse. This is doc 55's 0.000
     mAP lesson, and it needs a test.
5. **sam3-finetune.** Concept-conditioned: training data is (image, noun phrase,
   instance masks).
   - **Feasibility decides the scope.** The model is 3.2 GB, gated, and the machine has
     15 GB of disk free (dev-environment memory). Its trainability through the installed
     library also has to be established.
   - If it cannot train locally, the feature ships the requirements, the preflight and a
     precise refusal, and hands the job to Wave 13's remote GPU runner.
6. **finetune-ui.** A Training tab mode "Fine-tune a foundation model":
   - pick the model → requirements card → recipe/dataset check → settings with defaults
     → progress → before/after comparison with overlays → name and save;
   - disk and memory are estimated before the click.
7. **finetune-for-agents.** MCP tools: `get_finetune_requirements(model)`,
   `check_dataset_for(model, dataset|recipe)`, `start_finetune` and `finetune_status`. The
   docstrings carry the requirements text, and the doc 63 guide gains a fine-tune recipe
   per model.

## Open Research

- **SAM 3:** is it trainable through the installed `transformers`, and at what memory?
  Its licence terms for fine-tuned derivatives also need checking.
- **DINOv3 licence:** do the terms permit saving and redistributing fine-tuned weights, and
  what does doc 54's obligations list need?
- **MPS:** SAM 2 decoder training speed and memory on this Mac, and whether GPU (doc 57) is
  a prerequisite for a usable experience.
- **Disk:** 15 GB is free and SAM 2.1 large is 856 MB per saved variant. Saving decoder-only
  deltas would make a fine-tuned SAM cost megabytes.
