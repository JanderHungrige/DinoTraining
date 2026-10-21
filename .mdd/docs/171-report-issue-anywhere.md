---
id: 171-report-issue-anywhere
title: Report an Issue from Settings, not Only Beside an Error
edition: DinoTraining
depends_on: [140-error-report]
relates: [164-settings-tab]
source_files:
  - apps/frontend/src/components/ReportIssuePanel.tsx
  - apps/frontend/src/tabs/SettingsTab.tsx
  - apps/desktop/src-tauri/src/error_report.rs
routes: []
models: []
test_files:
  - apps/frontend/src/components/ReportIssuePanel.test.tsx
  - apps/desktop/src-tauri/src/error_report.rs
data_flow: greenfield
last_synced: 2026-10-21
status: complete
phase: all
mdd_version: 11
tags: [settings, github, issues, feedback]
path: Settings/ReportIssue
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 171 — Report an Issue from Settings

## Jan (2026-10-21)

"Do we have a report-an-issue button? That would send an issue to our git, or open the
GitHub issue page. Whatever is easier."

## What there was

Doc 140: "Report an issue" beside an **error**. It opens a prefilled GitHub issue (the
error, the version, the OS, the log's last lines, the home folder replaced by `~`) in the
browser. Without an error there was no way to it.

## Now

- **Settings → "Feedback"**: "Report an issue or suggest an idea", the same command
  (`report_issue`) with no error message.
- **Without a message** the issue has no "The error" section and no `bug` label (it may
  be an idea); the version, OS and log stay.
- **Outside the desktop app** (web dev) the button is a plain link to GitHub's new-issue
  page.
- The issue is never posted from the app: a token in a public app is a secret given away
  (doc 140). The user needs a GitHub account.

## Built (2026-10-21)

- `ReportIssuePanel` in Settings; `error_report.rs` drops the error section and the
  `bug` label for an empty message.
- **Tests:** `ReportIssuePanel.test.tsx` (desktop: `report_issue` with no message; web:
  the link); Rust `a_report_without_an_error_has_no_error_section_and_no_bug_label`.
- **In the running app** (web): Settings shows "Feedback" with the link to the new-issue
  page.
