# ADR 0018: Persist configuration and identity in versioned stores, keep no history

- Status: Accepted
- Supersedes: ADR 0004

## Context

ADR 0004 proposed converging on SQLite for configuration, registries,
identities and "selected history", and left the questions that decide it open:
which storage contracts the retained runtime needs, which data needs
transactional durability, what history belongs in the core, whether Recorder
can go, and what backup and migration mean. Wave 4 made the runtime concrete,
so they can be answered from the tree rather than in the abstract.

**What the runtime writes.** Every durable datum outside the user's YAML goes
through `helpers/storage.Store`: a versioned JSON document under `.storage/`,
one per concern. The auth store and the credential and MFA providers; core
configuration; config entries; the device, entity, area, floor, label,
category and issue registries; restore state; the `person`, `zone` and `tag`
collections; application credentials; HTTP, network, logger and camera
settings; exposed entities; and Bluetooth's scanner and passive-update caches.
One file sits outside `.storage/`: `ip_bans.yaml`, which HTTP appends to when
it bans an address. Everything else the runtime writes is derived or
requested — MQTT materializes certificates from its config entry into a
temporary directory, and the camera snapshot and record actions write where
the caller asks — and the retained integrations keep no files of their own.

**How it writes.** Each save replaces the whole document through a temporary
file and a rename, so a document is either the old one or the new one, never a
mix. The auth, registry, core-configuration, HTTP and network stores also
flush to disk before the rename. Saves are coalesced and forced out on stop.
Every document carries a major and minor version with its own migration, and a
document written by a newer major version is refused rather than misread. For
the registries, restore state and config entries, bootstrap then starts
recovery mode (ADR 0016) and leaves the file untouched; any other store fails
the setup of the integration that owns it.

**What Recorder was.** The one other persistence layer was Recorder: SQLite
through SQLAlchemy, holding states, events and long-term statistics. It was
never a default, so an ha-lite instance ran without it unless someone
configured it. Inside the retained tree it had three readers, none of them
required: `sensor/recorder.py` compiling statistics, `kitchen_sink` writing
demo statistics, and a best-effort query in `helpers/condition.py` that primed
`for:` durations from history when Recorder happened to be set up. Its product
consumers — history, logbook, energy — left in Wave 3.

## Decision

**The persistence contract is the store.** ha-lite's durable state is the
configuration directory: the user's YAML and `secrets.yaml`, the versioned
documents under `.storage/`, and `ip_bans.yaml`. Nothing else holds state the
runtime needs after a restart.

The data falls into three classes with different obligations:

| Class | What | Obligation |
|---|---|---|
| Configuration | YAML, core configuration, config entries | Durable across restarts and upgrades; migrated per document |
| Identity | auth, the registries, application credentials | Durable and flushed before replace; loss is a re-onboarding |
| Operational state | restore state, discovery caches, log levels | Best effort; loss costs a warm-up, not correctness |

There are no cross-document transactions. Each document is consistent on its
own, and the registries already tolerate references into each other that a
crash left behind, as upstream always has.

**History is not persisted by the core.** Recorder, its statistics and the
`sensor` statistics platform are removed, with SQLAlchemy and the other
dependencies only Recorder needed. States and events are published, not
kept: a client that wants history subscribes over the WebSocket API or MCP
and stores what it needs, the same way decisions left the core in ADR 0002.
Conditions anchor `for:` durations to the current state's timestamp; one that
was already true before ha-lite started counts from that state, not from an
earlier recorded one.

**SQLite is not introduced.** A single database file was ADR 0004's way to
simplify persistence. The inventory shows it would replace a few dozen small,
independently versioned documents with a schema that has to migrate as one,
and buy transactions nothing in the runtime asks for. If a retained contract
ever needs atomicity across documents, that is the point to revisit.

**Backup is a copy of the configuration directory.** Stop ha-lite, copy the
directory, and restore it by copying it back before starting. There is no
backup integration or API: like creating the owner (ADR 0016), it is an
operator action at the filesystem, which is already the root of trust.
`.storage/auth` holds password hashes and refresh tokens and `secrets.yaml`
holds secrets, so a backup is as sensitive as the directory itself. Restoring
an older copy is safe; the stores migrate forward. Restoring into an older
ha-lite is not: it refuses stores a newer major version wrote.

## Consequences

The runtime has one persistence mechanism, and it is the one Home Assistant's
core already uses for everything that must survive. No database driver, ORM,
migration history or statistics compiler ships with ha-lite, and bootstrap
has no Recorder stage to order the other integrations around.

Anything that relied on history in-process loses it. The `for:` priming is the
visible case: after a restart, a condition such as "door open for 10 minutes"
is anchored to the state the door was restored or reported in, which is the
same conservative answer upstream gives when Recorder is not set up. An agent
that needs to know how long something has been true across restarts must keep
that itself.

`Entity._unrecorded_attributes` and the `recorder_*` event names stay in core
as inert upstream API. Integrations still declare them, and removing them
would edit files for no behavioral gain (ADR 0014).

Retained integrations that grow their own persistence must use `Store`, with a
version and a migration, so the contract stays one mechanism.
