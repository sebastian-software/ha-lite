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

Only hard edges grow the closure. This distinction is not cosmetic. When the
tool was introduced, a single deferred import of `cloud` in `http/__init__.py`
— a repairs check that ran when SSL was configured without a URL — would have
dragged `cloud`, `alexa`, `google_assistant`, `tts`, `stt`, `backup` and
`assist_pipeline` into the retained set, inflating the closure from 78 domains
to 93 and making Wave 4 look far more constrained than it was. Treating that
edge as soft is what showed the coupling was removable; #19 then removed it.

Soft edges are not discarded. They are reported as **latent coupling**: the
things that would widen the closure if they ever hardened.

## What the import graph cannot see

Some platforms are loaded **by name**, through `async_get_platform`, and never
imported. `helpers/trigger.py` looks for `<domain>/trigger.py`, `condition.py`
does the same for conditions, and the runtime then dispatches to whatever it
finds. No edge exists, so the closure is blind to them.

This is not a bug in the closure: providing a platform is genuinely not a
dependency. Nothing in the retained runtime *requires* any particular provider,
so counting these as hard edges would drag every domain shipping a
`trigger.py` into the retained set. But deleting a provider removes a
capability **without breaking a single import**, which the closure alone would
never warn about.

#19 found this the expensive way. Deleting Template also removed
`template/trigger.py`, and with it `platform: template` for
`websocket_api.subscribe_trigger` — noticed only because one test happened to
use it.

The tool therefore reports **capability at risk** separately: providers of
runtime-resolved platforms that sit outside the closure. The platforms it
watches are listed in `cross_cutting_platforms` in the config. Self-scoped
platforms are deliberately excluded — `config_flow`, `diagnostics` and
`application_credentials` only extend their own integration, so they leave
with it, and 939 config-flow warnings would be noise.

### The device-class providers

The first run of this report surfaced something larger than the Template case.
Fourteen `integration_type: system` components sit outside the closure and
exist *only* to provide triggers and conditions over entity device classes:

`battery`, `door`, `doorbell`, `garage_door`, `gate`, `humidity`,
`illuminance`, `moisture`, `motion`, `occupancy`, `power`, `temperature`,
`vibration`, `window`

`motion/trigger.py`, for example, is twenty lines that define `motion.detected`
and `motion.cleared` over `binary_sensor` entities whose device class is
motion. It imports `binary_sensor`; `binary_sensor` does not import it. That
direction is exactly why the closure cannot see it.

These are plausibly substrate rather than product — "trigger when motion is
detected" is the kind of primitive a device runtime exposes to an agent — and
they are already in bootstrap's `DEFAULT_INTEGRATIONS`. Whether they become
roots is an open decision, not something the tool should assume. Until it is
taken, #27 must not delete them by reachability alone.

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
| Component domains in tree | 1,488 |
| Declared roots | 54 |
| Retained closure | 73 |
| Deletion candidates | 1,415 |

Of the 19 transitively required domains, 8 are `retained`, 6 are `adapter` and 5 are `patch_required`.

### What this says about Wave 4

The closure is small — 5% of the tree. The 1,415 candidates outside it are
reachable from no retained root, which is the evidence #27 needs to delete in
bulk instead of one directory at a time.

Reachability is necessary but not sufficient. 47 of those candidates provide a
runtime-resolved platform, so #27 must work the capability-at-risk list as well
as the closure: deleting them breaks nothing and still costs something.

The closure is also not yet minimal. Six of its members are held in only by
platform-adapter files: `condition.py`, `trigger.py`, `device_action.py`,
`device_trigger.py`, `media_source.py`. This is the same shape as the
per-integration `logbook.py` files removed in #21 — the adapter is deletable
independently of the domain that hosts it, and the target leaves with it.
#19 confirmed the pattern by removing the five `input_*` helpers this way:
dropping one entry from each domain's `_domain_specs` was enough to make them
fall out of the closure, after which they could simply be deleted.

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
