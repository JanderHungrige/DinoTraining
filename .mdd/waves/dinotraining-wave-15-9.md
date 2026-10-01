---
id: dinotraining-wave-15-9
title: "Wave 15.9: Cloud datasets — link an S3 (or similar) dataset, fetch pictures in batches, save annotations back"
initiative: dinotraining
initiative_version: 15
status: planned
depends_on: dinotraining-wave-15-8
demo_state: "A dataset in an S3 bucket (or an S3-compatible store such as MinIO, Wasabi or Cloudflare R2) is linked instead of downloaded: the app lists it, fetches pictures in batches as the Studio, Inspect, training and the Generator need them, keeps a bounded local cache, and saves annotations back to the bucket, so a large set never has to fit on the laptop."
created: 2026-10-01
hash: 648e8969
---

# Wave 15.9: Cloud datasets (plan only, to be detailed after Wave 15.8)

**Jan's request (2026-10-01):**
- "For large datasets that are saved in an S3, or somewhere else, we do not download the
  whole dataset, but give the user an option to connect to the cloud set and retrieve
  images in batches as needed."
- "The annotated data should then also be saveable to a cloud storage."

## Scope to settle when planning in detail

- **Stores:** S3 and S3-compatible (MinIO, Wasabi, Cloudflare R2, Ceph) first, through
  one client. Azure Blob and Google Cloud Storage are candidates, if asked for.
- **Linking:** a "Link a cloud dataset" next to doc 136's import, with
  - the bucket, a prefix and the region or endpoint;
  - credentials kept in `.env` or the OS keychain, never in the database or the logs
    (CLAUDE.md: secrets);
  - the same format detection as doc 136, run on the listing and the annotation files
    only.
- **Fetching:**
  - pictures on demand, a batch ahead of where the user or the job is;
  - a size-bounded LRU cache on disk, with the bound in the settings;
  - training streams batches instead of copying the set first, cooperating with the
    feature cache (doc 11).
- **Saving back:** annotations as COCO, plus the app's manifest, to a chosen prefix,
  explicitly or after each save. Conflicts when two people annotate the same bucket are
  detected, never silently overwritten.
- **Offline:** a linked dataset works from its cache and says what is missing.
- **The job runner seam** (CLAUDE.md: hyperscaler later) is where remote training will
  plug in. This wave only makes the data remote.
