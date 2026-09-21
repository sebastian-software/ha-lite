# Architecture decision records

Each record states one decision, the context that forced it and what it costs.
Records are append-only: a decision that turns out wrong gets a new record that
supersedes it, so the reasoning stays readable after the fact.

Format follows ADR 0001: title, `Status`, `Date`, then `Context`, `Decision`,
`Consequences`. Status is `Proposed`, `Accepted` or `Superseded by NNNN`.

| # | Decision | Status |
|---|---|---|
| [0001](0001-headless-device-core.md) | Define ha-lite as a headless device core | Accepted |
| [0002](0002-externalize-automation.md) | Keep automation and decision making outside the core | Accepted |
| [0003](0003-reduction-over-compatibility.md) | Prefer explicit reduction over maximum upstream compatibility | Accepted |
| [0004](0004-persistence-direction.md) | Converge toward simple SQLite-backed persistence | Proposed |
| [0005](0005-preserve-runtime-scheduling.md) | Distinguish runtime scheduling from user automation | Accepted |
| [0006](0006-integration-compatibility-boundary.md) | Preserve Home Assistant integration contracts before replacing them | Accepted |
| [0007](0007-headless-bootstrap.md) | Make bootstrap headless rather than merely disabling frontend | Accepted |
| [0008](0008-tests-define-retained-contract.md) | Use tests to define the retained runtime contract | Accepted |
| [0009](0009-mcp-core-control-surface.md) | MCP is a core headless control surface | Accepted |
| [0010](0010-closure-is-the-deletion-authority.md) | Let the computed closure decide what may be deleted | Accepted |
| [0011](0011-platforms-are-capabilities-not-dependencies.md) | Treat runtime-resolved platforms as capabilities, not dependencies | Accepted |
| [0012](0012-retain-device-class-semantics.md) | Retain the device-class trigger and condition vocabulary | Accepted |

## How these relate to the rest of the documentation

- ADRs say **why**, once, and do not change when the tree does.
- [`docs/architecture/scope-matrix.md`](../architecture/scope-matrix.md) says
  **what** is kept or removed, per component.
- [`docs/architecture/retained-closure.md`](../architecture/retained-closure.md)
  and its generated `retained-closure.json` say **what the tree currently
  proves**, and are regenerated on every change.

When the three disagree, the closure is the evidence, the matrix is the intent,
and the ADR is the reasoning that has to be revisited.
