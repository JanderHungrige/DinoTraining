---
id: dinotraining-wave-9
title: "Wave 9: Website & Hyperscaler Compute/Storage"
initiative: dinotraining
initiative_version: 5
status: planned
depends_on: dinotraining-wave-8
demo_state: "The app runs as a website; a user connects a cloud GPU for training and cloud object storage for datasets/models."
created: 2026-08-14
hash: fc491774
---

# Wave 9: Website & Hyperscaler Compute/Storage

## Demo-State

The same React + FastAPI core is deployed as a website. A signed-in user connects a
hyperscaler account (AWS / GCP / Azure), runs training on a remote GPU via the pluggable job
runner from Wave 2, and stores datasets/models in cloud object storage. Annotation and
inference work in the browser against the hosted backend.
*(Not complete until this can be manually demonstrated.)*

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | web-deployment | — | planned | — |
| 2 | user-accounts-auth | — | planned | web-deployment |
| 3 | cloud-storage-connector | — | planned | web-deployment |
| 4 | remote-gpu-job-runner | — | planned | web-deployment |
| 5 | multi-tenant-datasets | — | planned | user-accounts-auth, cloud-storage-connector |

### Feature notes

- Deploy the React + FastAPI core (Docker/GHCR, matching your funding-tender-tracker pattern).
- Accounts + auth (deferred design; likely JWT per your global standards).
- Cloud object storage connector (S3 / GCS / Azure Blob) for datasets + checkpoints.
- Remote GPU job runner implementing the Wave 2 runner interface.
- Multi-tenant isolation of datasets/models.

## Open Research

- Which hyperscaler(s) first; managed GPU (SageMaker / Vertex / Azure ML) vs. raw VMs.
- Cost controls + job lifecycle; storage cost of large datasets/checkpoints.
- This is the explicitly-"later" wave — revisit scope before planning.
