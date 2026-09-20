# Retained dependency closure

## Purpose

`docs/architecture/overview.md` states that the import graph is authoritative
when deciding whether code can be removed. This document describes the tool
that produces that graph and what its current output says.

The closure answers one question: **which integration domains must survive so
the retained runtime still works?** Everything outside it is a Wave 4 deletion
candidate (#27), identified by reachability rather than by directory name.

## Running it

```bash
python3 script/ha_lite_closure.py            # human-readable report
python3 script/ha_lite_closure.py --check    # CI gate, non-zero on findings
python3 script/ha_lite_closure.py --json     # machine-readable closure
python3 script/ha_lite_closure.py --write docs/architecture/retained-closure.json
```

The generated `retained-closure.json` is committed. CI regenerates it and fails
on drift, so the checked-in allowlist always matches the tree.

## How the closure is built

Two graphs feed it, as the overview requires:

- **declared edges** from `manifest.json` (`dependencies`, `after_dependencies`)
- **actual edges** from Python imports, parsed with `ast` rather than regex so
  multiline imports and aliases are handled correctly

Import edges are classified by how strongly they bind:

| Kind | Grows the closure | Why |
|---|---|---|
| `dependencies` | yes | Declared hard requirement. |
| `import_runtime` | yes | Module-level import; the module cannot load without it. |
| `after_dependencies` | no | Ordering hint, not a requirement. |
| `import_deferred` | no | Function-local import; removable without restructuring the module. |
| `import_typing` | no | Guarded by `TYPE_CHECKING`; never executes. |

Only hard edges grow the closure. This distinction is not cosmetic. A single
deferred import of `cloud` in `http/__init__.py` — a repairs check that runs
when SSL is configured without a URL — would otherwise drag `cloud`, `alexa`,
`google_assistant`, `tts`, `stt`, `backup` and `assist_pipeline` into the
retained set. Counting it as hard coupling would inflate the closure from 78
domains to 93 and make Wave 4 look far more constrained than it is.

Soft edges are not discarded. They are reported as **latent coupling**: the
things that would widen the closure if they ever hardened.

## Roots

Roots are declared in `script/ha_lite_closure_config.json` and mirror the job
matrices in `.github/workflows/ha-lite-ci.yml`. What CI protects is what
ha-lite promises to keep working, so the two should not drift apart.

| Category | Count |
|---|---|
| Entity-domain substrate | 26 |
| Retained integrations | 6 |
| Runtime infrastructure | 22 |

## The gate

Every domain that enters the closure without being a root needs a reviewed
entry in `accepted_transitive`, with a status and a reason:

- `retained` — part of the runtime; expected to stay
- `adapter` — the coupling lives in a removable platform-adapter file, so the
  target leaves with that file rather than on its own
- `patch_required` — genuine coupling that needs a decoupling change first

A domain reaching the closure without an entry fails the check. So does an
entry that is no longer reachable, which keeps the config from rotting. This
is what makes new coupling from retained code into an unreviewed component a
build failure rather than a discovery made months later.

## Current state

| Metric | Count |
|---|---|
| Component domains in tree | 1,502 |
| Declared roots | 54 |
| Retained closure | 78 |
| Deletion candidates | 1,424 |

Of the 24 transitively required domains, 8 are `retained`, 11 are `adapter`
and 5 are `patch_required`.

### What this says about Wave 4

The closure is small — 5% of the tree. The 1,424 candidates outside it are
reachable from no retained root, which is the evidence #27 needs to delete in
bulk instead of one directory at a time.

The closure is also not yet minimal. Eleven of its members are held in only by
platform-adapter files: `condition.py`, `trigger.py`, `device_action.py`,
`device_trigger.py`, `media_source.py`. This is the same shape as the
per-integration `logbook.py` files removed in #21 — the adapter is deletable
independently of the domain that hosts it, and the target leaves with it.
Those eleven should fall out of the closure during Waves 3 and 4 rather than
needing separate decoupling work.

The five `patch_required` members are the real blockers, and
`dependency-findings-2026.9.3.md` predicted four of them:

- `file_upload` ← MQTT certificate configuration UX (#22)
- `hassio` ← Matter add-on lifecycle (#25)
- `onboarding` ← Matter config flow reading onboarding state (#22)
- `device_tracker` ← DHCP discovery watching device_tracker registrations (#20)
- `backup` ← reached only through `hassio`, so it leaves with that patch unless
  headless backup semantics keep it (#30)

`device_tracker` is the one the findings document did not anticipate. It is
also the one that cannot be solved by deleting an adapter file: `dhcp/__init__`
imports it at module level to watch device_tracker registrations during
discovery.

### Entity domains missing from CI

The closure surfaced three domains MQTT implements that the CI entity-domain
matrix does not cover: `humidifier`, `lawn_mower` and `infrared`. All three are
`integration_type: entity` — substrate, not products. They are retained, but
they are currently retained without test protection.
