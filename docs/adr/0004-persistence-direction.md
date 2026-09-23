# ADR 0004: Converge toward simple SQLite-backed persistence

- Status: Superseded by 0018

ADR 0018 answers the open questions below from the reduced tree: the
persistence contract is the versioned JSON stores, Recorder is removed, and
SQLite is not introduced.

## Context

Home Assistant has multiple persistence concerns, including JSON-backed storage for configuration/runtime metadata and Recorder storage for history/statistics. ha-lite aims for a small installable server with minimal operational machinery.

## Decision

Do not block the initial Home Assistant reduction on a storage rewrite.

Long term, investigate SQLite as the primary durable store for configuration, registries, identities and selected history. Runtime state and event fan-out remain memory-oriented.

The desired property is a simple local persistence model, not a dogmatic "exactly one file at every instant" requirement.

## Open questions

- Which HA storage contracts are required by retained integrations?
- Which data needs transactional durability?
- What history, if any, belongs in the core?
- Can recorder/statistics be removed entirely before a smaller history model is introduced?
- What are the backup/restore and schema migration semantics?
