---
generated: 2026-08-18
doc_count: 18
connection_count: 40
overlap_count: 17
---

# Connections

## Path Tree

```
Admin/Models
└── Models  02-model-manager  complete
Inference/Engine
└── Engine  16-inference-engine  complete
Inference/Input
└── Input  17-image-input-source  complete
Meta/Schema
└── Schema  00-frontmatter-spec  complete
Platform/Datasets
└── Datasets  03-dataset-store  complete
Platform/Shell
└── Shell  01-app-shell  complete
Studio/Annotation
├── Annotation  04-grounding-dino-annotator  complete
└── Annotation  06-annotation-workflow  complete
Studio/Canvas
└── Canvas  05-annotation-canvas  complete
Training/Backbone
└── Backbone  07-backbone-feature-extractor  complete
Training/Heads
├── Heads  08-head-registry  complete
├── Heads  09-head-implementations  complete
├── Heads  12-head-instance-registry  complete
└── Heads  15-head-catalog-import  complete
Training/Preprocessing
└── Preprocessing  10-preprocessing-pipeline  complete
Training/Runner
├── Runner  11-training-job-runner  complete
└── Runner  13-training-metrics-stream  complete
Training/UI
└── UI  14-trainer-config-ui  complete
```

## Dependency Graph

```mermaid
graph TD
    D00["00-frontmatter-spec"]:::complete
    D01["01-app-shell"]:::complete
    D02["02-model-manager"]:::complete
    D03["03-dataset-store"]:::complete
    D04["04-grounding-dino-annotator"]:::complete
    D05["05-annotation-canvas"]:::complete
    D06["06-annotation-workflow"]:::complete
    D07["07-backbone-feature-extractor"]:::complete
    D08["08-head-registry"]:::complete
    D09["09-head-implementations"]:::complete
    D10["10-preprocessing-pipeline"]:::complete
    D11["11-training-job-runner"]:::complete
    D12["12-head-instance-registry"]:::complete
    D13["13-training-metrics-stream"]:::complete
    D14["14-trainer-config-ui"]:::complete
    D15["15-head-catalog-import"]:::complete
    D16["16-inference-engine"]:::complete
    D17["17-image-input-source"]:::complete
    D01 --> D02
    D01 --> D03
    D02 --> D04
    D03 --> D04
    D01 --> D05
    D01 --> D06
    D03 --> D06
    D04 --> D06
    D05 --> D06
    D01 --> D07
    D02 --> D07
    D07 --> D08
    D07 --> D09
    D08 --> D09
    D07 --> D10
    D08 --> D10
    D03 --> D11
    D07 --> D11
    D08 --> D11
    D09 --> D11
    D10 --> D11
    D03 --> D12
    D08 --> D12
    D11 --> D12
    D08 --> D13
    D11 --> D13
    D12 --> D13
    D08 --> D14
    D12 --> D14
    D13 --> D14
    D07 --> D15
    D08 --> D15
    D09 --> D15
    D12 --> D15
    D07 --> D16
    D08 --> D16
    D09 --> D16
    D10 --> D16
    D12 --> D16
    D16 --> D17
    classDef complete fill:#00e5cc,color:#000
    classDef in_progress fill:#ffaa00,color:#000
    classDef draft fill:#888,color:#fff
    classDef deprecated fill:#555,color:#aaa
```

## Source File Overlap

- `apps/frontend/src/api/client.ts` — 01-app-shell, 13-training-metrics-stream
- `apps/frontend/src/api/headInstances.ts` — 12-head-instance-registry, 15-head-catalog-import
- `apps/frontend/src/api/types.ts` — 01-app-shell, 07-backbone-feature-extractor
- `apps/frontend/src/components/SessionSetup.tsx` — 06-annotation-workflow, 17-image-input-source
- `apps/frontend/src/styles.css` — 01-app-shell, 05-annotation-canvas, 06-annotation-workflow, 14-trainer-config-ui, 15-head-catalog-import, 17-image-input-source
- `apps/frontend/src/tabs/AdminTab.tsx` — 01-app-shell, 02-model-manager, 15-head-catalog-import
- `apps/frontend/src/tabs/AnnotationStudioTab.tsx` — 01-app-shell, 06-annotation-workflow
- `apps/frontend/src/tabs/HeadTrainerTab.tsx` — 01-app-shell, 14-trainer-config-ui
- `apps/frontend/src/tabs/InferenceViewerTab.tsx` — 01-app-shell, 17-image-input-source
- `backend/app/api/v1/inference.py` — 16-inference-engine, 17-image-input-source
- `backend/app/api/v1/router.py` — 01-app-shell, 07-backbone-feature-extractor, 08-head-registry, 12-head-instance-registry, 13-training-metrics-stream, 15-head-catalog-import, 16-inference-engine
- `backend/app/datasets/db.py` — 03-dataset-store, 12-head-instance-registry
- `backend/app/ml/heads/builders.py` — 09-head-implementations, 15-head-catalog-import
- `backend/app/ml/heads/registry.py` — 08-head-registry, 15-head-catalog-import
- `backend/app/ml/preprocess.py` — 10-preprocessing-pipeline, 16-inference-engine
- `backend/app/ml/training/job.py` — 11-training-job-runner, 13-training-metrics-stream
- `backend/app/ml/training/runner.py` — 11-training-job-runner, 13-training-metrics-stream, 16-inference-engine

## Warnings

(none)
