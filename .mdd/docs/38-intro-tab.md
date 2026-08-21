---
id: 38-intro-tab
title: Intro Tab — What This Is, For Someone Who Has Never Seen It
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7
wave_status: in_progress
depends_on: [01-app-shell]
relates: [39-prompt-guidance, 07-backbone-feature-extractor, 08-head-registry]
source_files:
  - apps/frontend/src/tabs/IntroTab.tsx
  - apps/frontend/src/tabs/introContent.ts
  - apps/frontend/src/tabs/tabs.ts
  - apps/frontend/src/App.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/tabs/IntroTab.test.tsx
  - apps/frontend/src/components/TabBar.test.tsx
data_flow: greenfield
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [onboarding, intro, documentation, accessibility, tabs, contrast]
path: Start Here
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "`INTRO_LIMITS` is prose with no mechanism behind it. A test asserts the list is non-empty and rendered, but nothing can check that an entry is still *true* — when a limitation is lifted it has to be deleted here by hand, in the same commit."
  - "The intro is not the default tab. Someone who launches, works, and relaunches never sees it unless they click. A first-run pointer was considered and declined: it needs persisted \"have I seen this\" state, which the app has no home for yet."
  - "Prose only — no runnable example. \"Try this on a sample image\" is better onboarding and needs a bundled image, a guard for no model installed, and re-checking every time a tab changes. Declined for this wave; revisit after Wave 8 settles the tabs."
sister_projects: []
---

# 38 — Intro Tab

## Purpose

Give someone who has never seen the app a page that explains what it does, what a frozen
backbone and a head actually are, why the stages run in that order — and what the app
cannot do yet.

## Architecture

**A sixth tab, not a first-run overlay.** An overlay is seen once and then in the way, and
the moment anyone actually wants this is three days in, when they have forgotten what
"frozen" meant. A tab is re-readable forever and free to skip.

It leads the tab bar because a first-time user reads left to right. It is deliberately
**not** `DEFAULT_TAB`: someone returning to work should land where the work is.

The prose lives in `introContent.ts` as data. Two reasons: the page stays under the line
limit, and a test can assert on **what it claims** rather than on markup. Every stage names
a real `TabId`, checked by the compiler, so a renamed or removed tab breaks the build
instead of leaving the intro pointing at nothing.

## Business Rules

1. **Every tab is described, and in tab-bar order.** The intro's own claim is "the tabs are
   in the order you use them"; if the bar is reordered and this is not, the claim becomes
   false rather than merely untidy. Two tests pin it — one for coverage, one for order — and
   the coverage one is what will fail when Wave 8 or 9 adds a seventh tab.
2. **Each stage says *why it is there*, not just what it does.** The order is the part that
   cannot be guessed from the UI.
3. **A stage's button reads its label from `getTab`**, never a duplicated string, so a tab
   rename moves both together.
4. **The limitations are part of the page.** Someone told that video is missing has been
   told; someone not told concludes the app is broken.
5. **Reading turns into doing.** Every stage links to the tab it describes.

## Data Flow

None. `IntroTab` takes one prop — `onNavigate` — and `App` passes `setActiveTab`. No fetch,
no state, no backend.

## Dependencies

- **01-app-shell** — the tab registry, the tab bar and its keyboard behaviour.

## Security

None.

## Verified

In the running app on 2026-08-20, in **both colour schemes**. "Start here" leads the bar,
the five stages render with working "Open …" buttons, and clicking one switches tabs.

**One real bug, found by looking rather than by a test.** The step number rendered as an
invisible digit: the style used `var(--accent-dim, …)`, and `--accent-dim` **does not
exist** — the palette has `--accent`, `--text-dim`, `--pending`, and no combination of
those. The hardcoded fallback then painted `#15803d` on `#14532d`: **contrast 1.9**, the
number present in the DOM and unreadable on screen. That is doc 05's Wave 1 bug exactly,
reproduced by inventing a variable name instead of checking the palette.

Fixed by pairing `--bg` with `--accent` — two variables that **flip together** with the
colour scheme, which is what makes the pairing safe rather than lucky. Measured after:
**4.68** in light, **10.39** in dark.

The same check found two pre-existing instances, both fixed here: `.tokenpanel__badge` used
`--warning`/`--warning-bg`, neither of which is defined anywhere, so its hardcoded fallback
could not follow the light scheme; and this wave's own `.badge--noncommercial` (doc 35) had
invented `--warn-bg`/`--warn-fg` the same way. Both now use the `color-mix` formula
`.badge--gated` already established.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
