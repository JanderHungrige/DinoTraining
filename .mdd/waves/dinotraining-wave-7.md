---
id: dinotraining-wave-7
title: "Wave 7: Onboarding & Input Polish"
initiative: dinotraining
initiative_version: 7
status: complete
depends_on: dinotraining-wave-6
demo_state: "Someone who has never seen the app opens an Intro tab, understands what a frozen backbone and a head are and why the stages run in that order, writes a Grounding DINO prompt for one label type and for several, and adds images by dragging them onto the window."
created: 2026-08-19
hash: 679f53a8
---

# Wave 7: Onboarding & Input Polish

## Demo-State

A first-time user opens the app and an **Intro tab** explains, in plain language, what the
five tabs are for, what a frozen backbone and a trained head actually are, and why the
stages run in the order they do. In the **Annotation Studio** the prompt field explains how
to ask for **one** label type versus **several**, in Grounding DINO's actual syntax. Images
can be added by **dragging them onto the window**, not only by typing a path or using the
native picker.
*(Not complete until this can be manually demonstrated.)*

## Why this wave is last before packaging, and not first

It is the cheapest group here and the most tempting to do early. It is scheduled late on
purpose.

An intro tab and prompt guidance **describe how the app works** — and Waves 5 and 6 both
change that. Wave 5 removes the prompt entirely when a trained head is chosen; Waves 4 and 6
add concept-prompted models whose prompting rules differ again. Written first, this wave
would be written twice, and the second version would be the one nobody remembers to update.

It must still land **before Wave 8**, because packaging is the point at which the app
reaches people who have never seen it and cannot ask the person who built it.

## Features (draft — refined in plan-wave)

| # | Feature | Depends on |
|---|---------|------------|
| 1 | intro-tab | — |
| 2 | prompt-guidance | — |
| 3 | drag-and-drop-input | — |

- **intro-tab** — "in detail, for dummies". The pipeline is not guessable: nothing today
  explains why a backbone is frozen, what a head *is*, why preprocessing is derived rather
  than configured, or why a trained head has no prompt. It should be honest about what the
  app cannot do yet, too.
- **prompt-guidance** — how to ask for one label type versus several. Grounding DINO's
  `a cat. a dog.` syntax is not guessable and the placeholder is currently the only hint.
  Must cover **which mode the user is in**, since by this wave a prompt is one of three
  possibilities (Grounding DINO text, a trained head with no prompt, a SAM 3 concept).
- **drag-and-drop-input** — feeds doc 17's existing input contract rather than a second one.

## Demonstrated — marked complete 2026-08-20, with one gap named

**Intro tab** (doc 38): "Start here" leads the tab bar, five stages with working "Open …"
buttons, checked in **both colour schemes**. Found and fixed a real contrast bug of doc 05's
exact shape — a step number painted `#15803d` on `#14532d`, **contrast 1.9**, because the
style used a `--accent-dim` variable that does not exist and fell back to a hardcoded pair.
Now `4.68` light / `10.39` dark. The same check turned up two more instances of invented
variables, both fixed.

**Prompt guidance** (doc 39): prompt mode shows Grounding DINO's syntax with
`aria-describedby`; head mode drops the field and the syntax hint together and names the
head's own classes — verified against the chess head, which correctly rendered
*"bishop, black-bishop, black-king, black-knight and 9 more"*.

**Drag-and-drop** (doc 40): ⚠️ **the desktop drop is not exercised.** The browser branch was
verified — no affordance offered, nothing else affected — and the types check against the
real `DragDropEvent`, with thirteen cases pinning `folderOf`. But performing an actual drag
onto the Tauri window needs a human, and nothing available in this session can do or observe
it. **This is the one thing in Wave 7 that wants a manual look.**

## Scoping settled 2026-08-20 (before execution)

The wave doc said **"decide before building"** for the drag-and-drop question. All three
open items were put to Jan and answered.

### Drag-and-drop is Tauri-only; the browser keeps the picker

Measured against the installed `@tauri-apps/api` 2.11.1: `getCurrentWebview()
.onDragDropEvent()` yields `{type: 'drop', paths: string[]}` — **real filesystem paths**,
which feed doc 17's existing contract with no conversion and no second contract. It also
emits `enter`/`leave`, so the drop target can show honest hover state.

The browser gives `File` objects with no path. Rather than add an upload endpoint — a
second input contract, the one doc 17 deliberately avoided, plus a temp-file lifecycle to
own — the drop zone is simply **not offered** where it cannot work. That is the pattern
`hasNativeDialog` already sets: the browse buttons disappear, the path field never does.
If browser input is ever wanted it belongs in Wave 9, where server-side files are already
part of the deal.

### The intro is a sixth tab, not an overlay

Discoverable forever and never in the way. The wave doc's own objection to an overlay — seen
once, then an obstacle — is the deciding argument, and a tab is also the cheapest thing to
keep correct as Waves 8 and 9 change the app. No first-run banner: it would need persisted
"have I seen this" state, which has no home here yet.

### The intro explains, it does not execute

"Try this on a sample image" was considered and declined. It needs a sample image in the
installer, a guard for when no model is downloaded, and it goes stale every time a tab
changes — which is precisely what Waves 8 and 9 will do. Prose that names the right tab
stays correct for free.

### Features, revised

| # | Doc | Feature | Depends on |
|---|---|---|---|
| 1 | 38 | intro-tab | — |
| 2 | 39 | prompt-guidance | — |
| 3 | 40 | drag-and-drop-input | — |

## Open Research

- **Drag-and-drop in the browser has no path.** Under Tauri a file drop yields real
  filesystem paths, which the path-based API takes directly. In the plain `web` dev mode —
  and in Wave 9 — a drop yields `File` objects with no path, which the current API cannot
  accept. Either an upload endpoint appears (a second input contract, which doc 17
  deliberately avoided) or the browser case stays picker-only. **Decide before building.**
- **Where the intro lives.** A sixth tab, or a first-run overlay, or both. A tab is
  discoverable forever; an overlay is seen once and then in the way.
- **Whether the intro should be executable** — "try this on a sample image" — which is much
  better onboarding and much more to maintain.
