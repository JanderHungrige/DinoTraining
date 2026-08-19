---
id: dinotraining-wave-7
title: "Wave 7: Onboarding & Input Polish"
initiative: dinotraining
initiative_version: 7
status: planned
depends_on: dinotraining-wave-6
demo_state: "Someone who has never seen the app opens an Intro tab, understands what a frozen backbone and a head are and why the stages run in that order, writes a Grounding DINO prompt for one label type and for several, and adds images by dragging them onto the window."
created: 2026-08-19
hash: d0e77abb
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
