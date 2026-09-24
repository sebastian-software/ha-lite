# ADR 0021: Ship the core and the integrations as separate, version-locked packages

- Status: Proposed

## Context

ADR 0020 keeps Home Assistant's integration catalog in the tree, and the
distribution follows the tree. One package carries 1,161 catalog integrations
with code, 35.0 MB of Python, next to a core of 8.4 MB. A deployment uses a
few of them. The rest costs little at runtime, since integrations load only
when set up, but it is shipped, installed and, in principle, audited by
everyone.

Home Assistant bundles its integrations for reasons that hold for ha-lite
too. Integrations use the core's internals directly, which amount to about
1,450 names. The core changes those internals every month, and it fixes all
integrations in the same change.
[upstream-integration-api.md](../architecture/upstream-integration-api.md)
collects the sources. The monorepo is what makes that lockstep possible.
ha-lite's CI relies on the same lockstep: every catalog suite runs against the
core in the same commit (ADR 0020).

What bundling ties together is two separate things: how the code is
developed and tested, and how it is delivered. ha-lite needs the first to stay
a monorepo. It does not need the second to be one package.

## Decision

Proposed:

- **The repository stays one repository, and CI stays as it is.** The catalog
  is developed and tested against the core in the same commit.
- **The distribution is split.** A release publishes, under one version:
  - a core package: everything but the catalog, including the discovery index
    for the whole catalog;
  - one package per catalog integration with code;
  - a meta-package that installs all of them.
- **Versions are locked, not stable.** An integration package requires
  exactly the core version it was built with. The core loads no integration
  package of another version. No stable integration API is promised.
- **Integration packages keep upstream's import paths.** A package installs
  `homeassistant/components/<domain>/`, where the loader already looks, so no
  integration and no test changes.
- **A missing integration is installed the way a missing requirement is**
  (ADR 0019): on first setup, or by an explicit command, and never with
  `--skip-pip`.

[split-distribution.md](../architecture/split-distribution.md) has the plan:
- the measured interface;
- the package layout;
- the three interface levels:
  1. the distribution contract;
  2. a gate that makes the code interface visible;
  3. a stable API, deferred;
- build, test and release;
- the steps and the open questions.

## Consequences

- An installation holds the core and the integrations it uses. The full
  installation remains available through the meta-package.
- Discovery still covers the whole catalog, because the index ships with the
  core. A device whose integration is not installed is recognised, and the
  core names the package that handles it.
- Every release publishes about 1,160 packages. Where they are published is
  open; see the plan.
- The loader gains a version check, and the requirements manager gains an
  install step. Both are ha-lite changes to upstream files, and both are
  small (ADR 0014).
- A stable API for integrations built outside this repository is out of scope.
  The level-2 gate records how much of the interface each upstream update
  moves. If third parties ever need a stable API, that record is the evidence
  to decide it with.
- This record becomes `Accepted` when step 1 of the plan lands: the
  distribution is renamed, and the build script and packaging job exist.
