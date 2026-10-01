---
id: 147-cloud-connection
title: Cloud Connection — An S3-Compatible, Azure Blob or Google Cloud Storage Account, Its Secret in .env, Tested Before Use
edition: DinoTraining
depends_on: []
relates: [148-cloud-dataset-link, 150-cloud-save-back, 24-hf-token-settings]
source_files:
  - backend/app/cloud/__init__.py
  - backend/app/cloud/connections.py
  - backend/app/cloud/storage.py
  - backend/app/cloud/errors.py
  - backend/app/api/v1/cloud.py
  - backend/app/api/v1/router.py
  - backend/app/datasets/schema.py
  - backend/pyproject.toml
  - backend/uv.lock
  - apps/frontend/src/api/cloud.ts
  - apps/frontend/src/components/CloudConnections.tsx
  - apps/frontend/src/tabs/ModelsTab.tsx
  - apps/frontend/src/i18n/en/cloud.ts
  - apps/frontend/src/i18n/de/cloud.ts
  - apps/frontend/src/i18n/catalogue.ts
  - apps/frontend/src/components/CloudConnectionForm.tsx
  - apps/frontend/src/api/cloud.ts
  - backend/app/i18n/de_cloud.py
  - backend/app/i18n/translate.py
routes:
  - GET /api/v1/cloud/connections
  - POST /api/v1/cloud/connections
  - PUT /api/v1/cloud/connections/{connection_id}
  - DELETE /api/v1/cloud/connections/{connection_id}
  - POST /api/v1/cloud/connections/{connection_id}/test
models: [cloud_connections]
test_files:
  - backend/tests/test_cloud_connections.py
  - apps/frontend/src/components/CloudConnections.test.tsx
data_flow: greenfield
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [cloud, s3, minio, r2, azure, gcs, credentials, secrets, storage]
path: Cloud/Connection
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**No real AWS, Azure or Google account was used.** S3 was exercised over its real protocol against Adobe's S3Mock (it accepts any credentials, so wrong keys were not tested live); MinIO's images now need a registry login. Azure and GCS are built from obstore's documented options and unit-tested; their first real test needs an account."
security_read_sites:
  - backend/app/cloud/connections.py (secrets read from .env; never returned, logged or stored in the database)
  - backend/app/cloud/errors.py (provider errors are worded without the request's credentials)
sister_projects: []
---

# 147 — Cloud Connection

## Purpose

- **Jan (2026-10-01):**
  - "connect to the cloud set and retrieve images in batches as needed";
  - "saveable to a cloud storage";
  - "please also add azure and google".
- **This doc is the account:** where the storage is and how to sign in. Linking a dataset
  in it is doc 148.

## One client for three kinds (open research, decided)

- **`obstore`** (Rust `object_store` behind Python), measured 2026-10-01:
  - **5 MB** on Windows, against **23 MB** for `boto3` + `azure-storage-blob` +
    `azure-identity` + `google-cloud-storage`;
  - one dependency;
  - list, get, put and **conditional put** (ETag / version) for all three.
- **`storage.py` wraps it** in five verbs: `list`, `get`, `put`, `put_if`, `head`. Docs
  148–150 never ask which kind a store is.
  - Its in-memory store serves the tests.

## A connection

- **Stored in a new table `cloud_connections`:**
  - `id`, `name`, `kind`;
  - the non-secret parts: an endpoint, a region, an Azure account name;
  - `created_at`.
  - **No secret is ever in the database.**
- **Kinds:**
  - **`s3`:** AWS S3, MinIO, Wasabi, Cloudflare R2, Ceph.
    - Endpoint: empty for AWS, else the URL.
    - Region: default `us-east-1`, or `auto` for R2.
    - Secrets: an access key ID and a secret access key.
  - **`azure`:** a storage account name, and an account key or a SAS token.
    - Endpoint: empty for Azure, or Azurite's URL.
  - **`gcs`:** a service account's JSON key (decision D4: base64 on one line in `.env`).
- **Secrets go to `.env`** (CLAUDE.md; as `HF_TOKEN`, doc 24), under
  `DINO_CLOUD_<ID>_<PART>`.
  - Reads report only *whether* each is set.
  - A `PUT` without a secret keeps the stored one.
  - `DELETE` removes the connection and its `.env` lines.
- **"Test connection"** (`POST …/{id}/test` with a bucket or container):
  - lists at most one key and answers `{ok, message}`;
  - says **plainly** what failed: the endpoint cannot be reached, the credentials are
    refused, no permission to list, the bucket does not exist, or the wrong region.
  - The message never echoes a secret.

## UI (Models & Datasets → Datasets, "Cloud storage", folded)

- **The list of connections:** name, kind, endpoint or account, "secret set".
  - Each row has Test, Edit and Delete (two clicks).
- **"Add a connection":**
  - the kind first, then only that kind's fields;
  - secrets as password fields; the GCS key as a file to choose or JSON to paste.
- **Test** asks for the bucket or container, then shows the answer under the row.

## Not here

- **MCP tools:** with linking (doc 148), where an agent has something to do with a
  connection.
- **The OS keychain:** decision D4. One mechanism to protect; the keychain could
  replace `.env` later behind the same API.

## Found while building

- **`DELETE` answered 204 with no body.** The app's client reads JSON from every answer,
  so it now answers `{"deleted": true}`.
- **A missing bucket was worded as "refused".** Listing a missing bucket returns
  `NoSuchBucket` inside a generic error, not as `NotFoundError`. It (and Azure's
  `ContainerNotFound`) is now worded "does not exist".
- **Cloud and export messages reached a German reader in English.** `de_cloud.py` adds
  them to doc 113's catalogue, including docs 138 and 142–145's refusals.
- **An unreachable endpoint** must fail in seconds: retries are bounded (2, 20 s) and the
  connection times out after 10 s.

## Verified (2026-10-01)

- **Backend (1961 tests, 10 new):**
  - **Secrets:** in and never out, in no response and no log line.
  - **Editing:** an empty secret keeps the stored one; deleting blanks the `.env` lines.
  - **Errors:** an unreachable endpoint said plainly and quickly.
  - **Refused:**
    - Azure without an account;
    - a secret part another kind has;
    - an endpoint without `http(s)://`;
    - a JSON that is no service account;
    - a key that is neither JSON nor base64.
  - **The GCS key:** pasted with line breaks, kept base64 on one line, read back intact.
  - **Storage verbs:**
    - create-only;
    - update-if-unchanged;
    - a stale write refused ("changed since it was last read");
    - "only if absent" refused once it exists;
    - head, list in pages, probe.
  - **Wording:** `NoSuchBucket` and `ContainerNotFound` worded "does not exist"; a German
    reader reads the test's and the refusal's message in German.
- **Frontend (1179 tests, 4 new):**
  - the list (kind, where, "Secret saved");
  - a test against a bucket;
  - Azure fields only for Azure;
  - a GCS key read from a file;
  - editing shows no secret, and the kind is fixed;
  - deleting in two clicks, in German.
- **Live:**
  - **`obstore` against the real S3 protocol** (Adobe S3Mock in Docker): list (pages),
    get, put, create-only, update-if-match, and a stale ETag refused by the server.
  - **In the app (German):**
    - a connection added through the form;
    - "Testen" against `photos`: "Verbunden mit photos: Es enthält Dateien (zum
      Beispiel …)";
    - against a missing bucket: "gibt-es-nicht gibt es nicht, oder dieses Konto sieht es
      nicht. (…)";
    - deleted, with its `.env` lines blanked and the secret absent from the backend log.
  - **Size:** `obstore` 5.1 MB on Windows, against 23 MB for the four official clients.
