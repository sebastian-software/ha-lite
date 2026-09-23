# Retained dependency closure

## Purpose

`docs/architecture/overview.md` states that the import graph is authoritative
when deciding whether code can be removed. This document describes the tool
that produces that graph and what its current output says.

The closure answers one question: **which integration domains must survive so
the retained runtime still works?** Wave 4 (#27) deleted everything outside
it, identified by reachability rather than by directory name, so the tree and
the closure are now the same set. A component outside the closure is a finding.

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

Core — everything under `homeassistant/` outside `components/` — is walked as
a pseudo-domain, `<core>`, because it is loaded unconditionally. Its hard edges
grow the closure like any root's, and its soft edges are latent coupling like
any member's.

Relative imports are resolved against the importing file's package, so
`from .components import api` in `bootstrap.py` counts exactly like its
absolute spelling. Inside a component they resolve to the component itself
and add nothing.

### Imports of components that are gone

The walk only follows edges into domains that exist, so an import of a deleted
component is invisible to it — and a deferred one fails only when its function
runs. Retained code (closure members and core) importing a component that is
not in the tree is therefore a finding of its own, **dangling**, whatever the
edge's strength. Only `after_dependencies` is exempt: the loader ignores an
ordering hint on a missing domain.

### What these rules found

The first version of the tool skipped relative imports, on the reasoning that
one cannot leave its component. That holds inside `components/` and not in
core. `bootstrap.py` pre-imports its components as `from .components import
...`, and one of them was `default_config`: resolving it pulled fifteen
unreviewed domains into the closure, among them the whole voice stack through
`default_config`'s manifest. The pre-import was dropped in #23; `default_config`
itself leaves in #22.

The same change surfaced `core_config.py` importing the deleted `frontend`
inside a storage migration. It was caught by a `broad-except`, so migrating a
pre-1.3 core store only logged an exception — and `tests/test_core_config.py`,
which was not in CI, failed on it.

The latent report used to cover closure members only, not core.
`helpers/service.py` imports five entity domains inside a function to validate
`supported_features` filters in `services.yaml`; all five sat outside the
closure, so deleting any of them would have broken service-description loading
for every domain, and nothing reported it. #23 removed `ai_task` and
`assist_satellite` from that import, and #27 removed `calendar`, `remote` and
`todo` when it deleted them.

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
Fifteen components sat outside the closure and existed almost entirely to
provide triggers and conditions over entity device classes:

`air_quality`, `battery`, `door`, `doorbell`, `garage_door`, `gate`,
`humidity`, `illuminance`, `moisture`, `motion`, `occupancy`, `power`,
`temperature`, `vibration`, `window`

`motion/trigger.py`, for example, is twenty lines that define `motion.detected`
and `motion.cleared` over `binary_sensor` entities whose device class is
motion. It imports `binary_sensor`; `binary_sensor` does not import it. That
direction is exactly why the closure cannot see it.

They are now roots. `binary_sensor` and `sensor` ship no `trigger.py` or
`condition.py` of their own — only the legacy device-automation platforms — so
these fifteen are the entire semantic vocabulary over the two most important
sensor domains, and `websocket_api` exposes it to external decision engines.
ADR 0012 records the decision and what it costs.

## Roots

Roots are declared in `script/ha_lite_closure_config.json`. Every root has a CI
job in `.github/workflows/ha-lite-ci.yml`: what CI protects is what ha-lite
promises to keep working, so a root without a job is a gap, not a shortcut.

| Category | Count |
|---|---|
| Entity-domain substrate | 33 |
| Retained integrations | 7 |
| Runtime infrastructure | 24 |
| Device-class semantics | 15 |
| Aggregation | 2 |
| Environment | 1 |
| Test fixtures | 2 |

`demo` and `kitchen_sink` are the one category that is not runtime. Retained
upstream suites set them up by name — `demo` as a stand-in domain in
config-entry tests and as the platform behind the `media_player`, `camera` and
`group` tests, `kitchen_sink` behind `group`'s lock tests — so deleting them by
reachability would have broken retained CI. Their platforms for domains
ha-lite does not retain are pruned, which keeps them from pulling anything into
the closure but themselves.

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
| Component domains in tree | 90 |
| Declared roots | 84 |
| Retained closure | 90 |
| Deletion candidates | 0 |

Of the 6 transitively required domains, 5 are `retained` and 1 is an `adapter`.
`recorder` was the seventh until #28 removed it (ADR 0018).

### Wave 4

Before Wave 4 the closure held 88 of 1,470 domains. #27 made three of the
other 1,382 roots — `demo` and `kitchen_sink` as test fixtures, `isal` for
HTTP (below) — and deleted the remaining 1,379 with their tests, brand
entries, generated matchers and requirements. The tree has held only the
closure since: the report lists no deletion candidates. `requirements_all.txt`
went from 1,146 pinned packages to 43.

From then on the relationship runs the other way. A component in the tree that
the closure does not reach was added without being declared, and the gate
reports it as **outside**: declare it a root and give it a CI job, or delete it.

The imports the deletion broke were the ones the latent-coupling report had
already listed: `helpers/service.py` into `calendar`, `remote` and `todo`, and
`helpers/network.py` and `helpers/system_info.py` into `hassio`. Deleting the
targets turned them into dangling findings, and the code behind them went.
What the report could not list were three kinds of coupling by name, in
strings:

- **Bootstrap.** Stage 0 names `isal`, `sentry` and `debugpy`, stage 1
  `mqtt_eventstream`, and the defaults every member of the generated `Platform`
  enum. Entity domains that left the tree also left the enum, and `sentry`,
  `debugpy` and `mqtt_eventstream` left bootstrap. `isal` was deleted at
  first and CI caught it: the integration does nothing but carry the `isal`
  package, which `http` loads for fast zlib compression, and without it HTTP
  logs a fallback warning on every start — which is what the `system_log`
  tests saw. It is a runtime-infrastructure root now.
  `tests/ha_lite/test_bootstrap_domains.py` checks every set bootstrap and the
  generated `configuration.yaml` name against this closure.
- **Test fixtures.** `demo`, `kitchen_sink` and the `testing_config` custom
  platforms named deleted domains; see the roots above.
- **Test doubles.** Some retained tests used a deleted integration as a
  convenient stand-in — `intent_script` to answer a custom intent,
  `shell_command` to register a service at runtime, `mjpeg` to exercise the
  stream proxy, `browser` as an integration to set up. Each now uses a handler,
  mock integration or plain view of its own. Four Bluetooth tests patched
  their matchers after a fixture had already set Bluetooth up, so they only
  ever passed against SwitchBot's generated matcher; the patch now applies
  first.

One `patch_required` member was left before Wave 4, and it was settled the
other way. `weather` is held in by the `temperature` and `humidity` triggers
and conditions, which declare a `DomainSpec` over weather entities. Patching
that out meant editing both platforms and 99 upstream test references, each a
conflict on every future import (ADR 0014), to save one entity domain. It is
entity-domain substrate instead, with a CI job.

### The capability-at-risk list, worked

ADR 0011 requires the list to be worked before a bulk deletion, not just read.
It named 29 providers outside the closure. `kitchen_sink` became a root and
lost its `backup` platform; the other 28 were deleted, for these reasons:

| Platform | Providers | Why the capability goes |
|---|---|---|
| `backup` | `backup` and its 12 storage agents; `hassio`, `zha` | A backup of ha-lite is a copy of its configuration directory (ADR 0018), not Home Assistant's backup product. `hassio` and `zha` leave with their integration. |
| `trigger`, `condition`, `intent`, `reproduce_state`, `significant_change` | `calendar`, `geo_location`, `remote`, `todo` | Entity domains no retained integration implements, so their vocabulary could never match an entity. |
| `trigger`, `condition` | `moon` | Computed like `sun`, but not device-relevant; ADR 0002 keeps `sun` for what solar elevation means to a PV site. |
| `intent`, `reproduce_state` | `shopping_list`, `alert` | Product features. |
| `trigger` | `knx`, `lg_netcast`, `litejet`, `samsungtv`, `webostv`, `zwave_js` | Device and hub triggers leave with their integration. |

### Coupling settled before Wave 4

#22 removed two `patch_required` members. `file_upload` was held only by
`bootstrap.py`'s pre-import once #25 moved MQTT to PEM text, and `onboarding`
by checks in `auth/login_flow.py`, `bluetooth/config_flow.py` and
`helpers/config_entry_flow.py` that all read "already onboarded" whenever
onboarding was not set up — which in ha-lite was always. Both are deleted, and
ADR 0016 records what replaced onboarding.

#25 resolved two more. `hassio` was held in by the Matter Server and Mosquitto
add-on paths in Matter and MQTT, and by `usb` listing the serial ports
Supervisor apps claim; all three paths are gone, and `backup`, reached only
through `hassio`, left with it. Wave 4 deleted both.
`dependency-findings-2026.9.3.md` had predicted the Matter and MQTT coupling;
the `usb` edge it did not.

`device_tracker` used to be a sixth, held in by DHCP discovery watching its
registrations. #20 resolved it the other way: `device_tracker` is an entity
domain MQTT implements, so it became a root rather than a patch.

### Entity domains that were retained without CI

The closure once surfaced three domains MQTT implements that the CI
entity-domain matrix did not cover: `humidifier`, `lawn_mower` and `infrared`.
Wave 3 added three more — `device_tracker`, `scene` and `tag` — and the same
argument applies to all six: an `integration_type: entity` domain a retained
integration implements is substrate, and recording it as transitive only
reflected which importer the walk happened to reach first.

All six are now roots with a job in the entity-domain matrix, alongside the two
`aggregation` roots. Every declared root has CI coverage.
