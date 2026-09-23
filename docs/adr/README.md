# Architecture decision records

Each record states one decision, the context that forced it and what it costs.

## These are living documents

ADRs here are **not immutable**. They carry no date and no version, and they are
not an append-only log. When reality moves, the record is edited to match.

That is a deliberate departure from the common ADR convention. The usual
argument for immutability is that a record should show what was known at the
time. This project does not need that: the commit history already shows it, and
the value of an ADR here is that it answers *why is the code like this* for
whoever reads it next. A record that describes a plan the tree no longer follows
does not preserve history, it just misleads.

So:

- **Edit a record when the decision it describes has been carried out.** Replace
  "X is a deletion candidate" with what happened to X. ADR 0002 does this.
- **Edit a record when it makes a claim the tree no longer supports.** A check
  that was true when written and is not true now is a bug in the document.
- **Write a new record when the decision itself changes**, and set the old one's
  status to `Superseded by NNNN` with a line pointing at it. Reversing a
  decision is not the same as keeping a record current.
- **Never rewrite a record to hide that the project changed its mind.** The
  point is accuracy, not tidiness.

Numbers are stable identifiers, not an ordering of importance, and are never
reused.

## Format

`# ADR NNNN: Title`, then `- Status:`, then `## Context`, `## Decision`,
`## Consequences`. Status is `Accepted`, `Proposed` or `Superseded by NNNN`.

No date field: these records are maintained, so a date would only ever be the
date someone last touched the file, which `git log` already answers better.

Records are written in English, like everything else in the repository
(ADR 0013).

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-headless-device-core.md) | Define ha-lite as a headless device core | Accepted |
| [0002](0002-externalize-automation.md) | Keep automation and decision making outside the core | Accepted |
| [0003](0003-reduction-over-compatibility.md) | Prefer explicit reduction over maximum upstream compatibility | Accepted |
| [0004](0004-persistence-direction.md) | Converge toward simple SQLite-backed persistence | Superseded by 0018 |
| [0005](0005-preserve-runtime-scheduling.md) | Distinguish runtime scheduling from user automation | Accepted |
| [0006](0006-integration-compatibility-boundary.md) | Preserve Home Assistant integration contracts before replacing them | Accepted |
| [0007](0007-headless-bootstrap.md) | Make bootstrap headless rather than merely disabling frontend | Accepted |
| [0008](0008-tests-define-retained-contract.md) | Use tests to define the retained runtime contract | Accepted |
| [0009](0009-mcp-core-control-surface.md) | MCP is a core headless control surface | Accepted |
| [0010](0010-closure-is-the-deletion-authority.md) | Let the computed closure decide what may be deleted | Accepted |
| [0011](0011-platforms-are-capabilities-not-dependencies.md) | Treat runtime-resolved platforms as capabilities, not dependencies | Accepted |
| [0012](0012-retain-device-class-semantics.md) | Retain the device-class trigger and condition vocabulary | Accepted |
| [0013](0013-english-is-the-project-language.md) | English is the project language | Accepted |
| [0014](0014-additive-checks-over-upstream-surgery.md) | Add checks in our own files rather than edit upstream ones | Accepted |
| [0015](0015-repository-conventions.md) | Follow the Sebastian Software repository conventions | Accepted |
| [0016](0016-headless-first-run-and-recovery.md) | Initialize, recover and administer ha-lite without a browser | Accepted |
| [0017](0017-oauth-lifecycle-anchor.md) | Keep one OAuth integration as the anchor for authorization | Accepted |
| [0018](0018-persistence-contract.md) | Persist configuration and identity in versioned stores, keep no history | Accepted |
| [0019](0019-configuration-and-dependencies.md) | Keep YAML as input, ship the closure's dependencies, gate both in CI | Accepted |

## How these relate to the rest of the documentation

- ADRs say **why**, and are kept current.
- [`docs/architecture/scope-matrix.md`](../architecture/scope-matrix.md) says
  **what** is kept or removed, per component.
- [`docs/architecture/retained-closure.md`](../architecture/retained-closure.md)
  and its generated `retained-closure.json` say **what the tree currently
  proves**, and are regenerated on every change.
- [`docs/architecture/roadmap.md`](../architecture/roadmap.md) says **what is
  still to do**, and which GitHub issue carries each open block.

When the three disagree, the closure is the evidence, the matrix is the intent,
and the ADR is what has to be brought back in line.

## What these records cannot tell you

ADRs 0001 through 0009 were all written into the repository's root commit, a
squashed import of 27,439 files. The frontend, Lovelace, automation and script
removals happened before that commit, so there is no per-change history for
them: those nine records are the only account of that reasoning, and they were
written after the fact rather than alongside it.

Everything from the second commit onward is reconstructable from the history.
