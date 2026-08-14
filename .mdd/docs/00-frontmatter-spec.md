---
id: 00-frontmatter-spec
title: Frontmatter Schema - Canonical Field Reference for All MDD Docs
edition: MDD
depends_on: []
relates: []
source_files: []
routes: []
models: []
test_files: []
data_flow: greenfield
last_synced: 2026-08-14
status: complete
phase: all
mdd_version: 11
tags: [schema, frontmatter, spec]
path: Meta/Schema
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# Frontmatter Schema Reference

Every `.mdd/docs/*.md` feature doc must start with this YAML frontmatter block.
Doc-generating phases (build, lifecycle, import-spec, plan) must read this file
before writing any frontmatter — never use embedded templates.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique doc ID matching the filename slug (e.g. `01-auth`) |
| `title` | string | Human-readable feature name |
| `edition` | `MDD` or `Both` | Which MDD edition this applies to |
| `depends_on` | string[] | IDs of feature docs this depends on (build order) |
| `relates` | string[] | IDs of docs that co-change with this one (not prerequisite - symmetric hint) |
| `source_files` | string[] | Source files this doc describes (relative to project root) |
| `routes` | string[] | API routes exposed by this feature |
| `models` | string[] | Database models used or defined by this feature |
| `test_files` | string[] | Test files covering this feature |
| `data_flow` | string | `greenfield`, `reads-existing`, `writes-existing`, or `mixed` |
| `last_synced` | date | ISO date when doc was last synced with source code |
| `status` | string | `draft`, `in_progress`, `complete`, or `deprecated` |
| `phase` | string | Build phase: `1`, `2`, `3`, or `all` |
| `mdd_version` | integer | MDD version when doc was last updated |
| `tags` | string[] | Domain concepts, technology names, feature names (no file paths or generic words) |
| `path` | string | Slash-delimited breadcrumb for navigation (e.g. `Auth/Login`) |
| `integration_contracts` | object[] | Contracts this doc consumes from other features |
| `satisfies_contracts` | object[] | Contracts this doc fulfills for other features |
| `security_read_sites` | string[] | Code locations where security-sensitive reads occur |
| `known_issues` | string[] | Known bugs or gaps (append-only - never remove) |

## satisfies_contracts Schema

```yaml
satisfies_contracts:
  - from: <feature-id>
    function: <function or endpoint name>
    when: <condition or trigger>
    status: pending   # or: done
    verified_at: ""   # or: "file:line" when status is done
```

Note: the field is `verified_at` (not `verified`). Status must be `pending` or `done`.

## relates Field

`relates` lists doc IDs that tend to change together with this doc. It is symmetric
and is a co-change hint, not a build dependency.

## Wave Frontmatter Schema

```yaml
id: <initiative>-wave-<N>
title: "Wave N: <title>"
initiative: <initiative-id>
initiative_version: <integer>
status: planned | in_progress | complete
depends_on: <previous-wave-id>
demo_state: "<one sentence: what must be demonstrable when this wave is done>"
created: <ISO date>
hash: <8-char sha256 of file content excluding hash line>
```

## Initiative Frontmatter Schema

```yaml
id: <initiative-id>
title: <title>
status: planned | in_progress | complete
version: <integer>
created: <ISO date>
hash: <8-char sha256>
```
