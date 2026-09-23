# Retained dependency closure

## Purpose

`docs/architecture/overview.md` states that the import graph is authoritative
when deciding whether code can be removed. This document describes the tool
that produces that graph and what its current output says.

The closure answers one question: **which integration domains does the
protected core need?** The roots are what CI runs in full, and the closure is
everything they pull in. Every other component in the tree is the **catalog**:
Home Assistant's integrations, kept as upstream ships them and loaded only when
a user sets them up (ADR 0020).

Wave 4 (#27) used the closure as the authority for deletion and removed every
component outside it, most device integrations among them. That was never the
goal. The catalog is back, and the closure now draws the line between the core
and the catalog instead of between the tree and the bin.

## Running it

```bash
python3 script/ha_lite_closure.py            # human-readable report
python3 script/ha_lite_closure.py --check    # CI gate, non-zero on findings
python3 script/ha_lite_closure.py --json     # machine-readable closure
python3 script/ha_lite_closure.py --write docs/architecture/retained-closure.json
```

The generated `retained-closure.json` is committed. CI regenerates it and fails
on drift, so the checked-in closure and catalog always match the tree.

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

The walk only follows edges into domains that exist, so an import of a
removed component is invisible to it — and a deferred one fails only when its
function runs. Any code in the tree — core, closure or catalog — importing a
component that is not in the tree is therefore a finding of its own,
**dangling**, whatever the edge's strength. Only `after_dependencies` is
exempt: the loader ignores an ordering hint on a missing domain.

For the catalog this is the entry condition. An integration that still imports
a removed product layer cannot load, so it stays out of the tree until it is
decoupled.

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
`todo` when it deleted them. ADR 0020 brought all three back, and the import
with them.

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
runtime-resolved platforms that sit in the catalog rather than the closure. The platforms it
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
| Entity-domain substrate | 39 |
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
reachability would have broken retained CI. Wave 4 pruned their platforms for
the domains it deleted; the platforms came back with those domains, and with
them `manual`, which demo's alarm panel builds on.

## The gate

Every domain that enters the closure without being a root needs a reviewed
entry in `accepted_transitive`, with a status and a reason:

- `retained` — part of the runtime; expected to stay
- `adapter` — the coupling lives in a removable platform-adapter file, so the
  target leaves with that file rather than on its own
- `patch_required` — genuine coupling that needs a decoupling change first

A domain reaching the closure without an entry fails the check. So does an
entry that is no longer reachable, which keeps the config from rotting. This
is what makes new coupling from core code into an unreviewed component a
build failure rather than a discovery made months later.

Two more findings guard the tree as a whole:

- **excluded** — a product layer ha-lite removed on purpose is in the tree
  again. The layers are listed under `excluded` in the config, grouped by what
  they served: presentation, automation, history, voice and AI, cloud and
  platform. The scope matrix gives each one's reason.
- **dangling** — code anywhere in the tree imports a component that is not
  there; see above.

A catalog member is not a finding. It needs no root and no reviewed entry, and
the `catalog` CI job runs its suite.

## Current state

| Metric | Count |
|---|---|
| Component domains in tree | 1,310 |
| Declared roots | 90 |
| Retained closure | 98 |
| Catalog | 1,212 |

Of the 8 transitively required domains, 7 are `retained` and 1 is an `adapter`.
`recorder` was one more until #28 removed it (ADR 0018). The tree count
includes 20 virtual integrations, which are a manifest pointing at another
integration and carry no code.

### Wave 4

Before Wave 4 the closure held 88 of 1,470 domains. #27 made three of the
other 1,382 roots — `demo` and `kitchen_sink` as test fixtures, `isal` for
HTTP (below) — and deleted the remaining 1,379 with their tests, brand
entries, generated matchers and requirements. The tree has held only the
closure since: the report lists no deletion candidates. `requirements_all.txt`
went from 1,146 pinned packages to 43.

From then on the relationship ran the other way: a component in the tree that
the closure did not reach was an **outside** finding. ADR 0020 retired that
finding when the catalog came back; see below.

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

### The catalog restored

ADR 0020 reversed Wave 4 for every component that could load again. The
candidates were the 1,377 components Wave 4 deleted, less `recorder`,
`hassio` and `backup`, which are excluded product layers. A candidate came
back when nothing it imports at module level or declares as a dependency is
missing from the tree, counting the other candidates as present. That brought
back 1,219 of them, and `media_source`, which Wave 3 had removed with the
voice stack, came back beside them.

Six restored components are entity domains — `calendar`, `geo_location`,
`image_processing`, `radio_frequency`, `remote` and `todo` — and became
entity-domain roots with CI jobs. `demo` and `kitchen_sink` got their
platforms for them back, and `manual`, which demo's alarm panel builds on, is
`accepted_transitive`. Bootstrap names `sentry` and `debugpy` in stage 0 and
`mqtt_eventstream` in stage 1 again, and leaves `calendar` and `todo` out of
its defaults as upstream does. Retained tests that Wave 4 had moved off a
deleted stand-in went back to upstream's version wherever the stand-in
returned (`shell_command`, `mjpeg`, `browser`, `shopping_list`, `todo`,
`calendar`), and kept ha-lite's version where it did not (`intent_script`,
`plant`, the Supervisor fixtures).

Four restored manifests listed a missing domain in `after_dependencies`, which
hassfest rejects: `bluetooth_adapters` (`esphome`) and `litellm`, `llama_cpp`
and `ovhcloud_ai_endpoints` (`assist_pipeline`). Those entries are removed;
the loader ignored them anyway. Brand files keep only the integrations in the
tree, and a brand left with fewer than two is removed, as hassfest requires.

158 integrations are still out. 120 import something that is gone, listed by
what they need; an integration appears once for each thing it needs:

| Needs | Kind | Integrations |
|---|---|---|
| `script` | removed layer | `elkm1`, `emulated_hue`, `homekit`, `intent_script`, `jvc_projector`, `lg_thinq`, `opensensemap`, `ring`, `roborock`, `smartthings`, `telegram_bot`, `tplink`, `unifiprotect`, `v2c`, `victron_gx`, `whirlpool`, `zwave_js` |
| `tts` | removed layer | `amazon_polly`, `baidu`, `elevenlabs`, `esphome`, `fish_audio`, `google_cloud`, `google_generative_ai_conversation`, `google_translate`, `marytts`, `microsoft`, `openai_conversation`, `picotts`, `smtp`, `voicerss`, `voip`, `wyoming`, `yandextts` |
| `recorder` | removed layer | `anglian_water`, `elvia`, `filter`, `history_stats`, `ista_ecotrend`, `mill`, `opower`, `plant`, `solaredge`, `sql`, `srp_energy`, `statistics`, `suez_water`, `tibber`, `usage_prediction`, `waterfurnace` |
| `automation` | removed layer | `airvisual`, `elkm1`, `homekit`, `jvc_projector`, `lg_thinq`, `opensensemap`, `ring`, `roborock`, `smartthings`, `tplink`, `unifiprotect`, `v2c`, `victron_gx`, `whirlpool`, `zwave_js` |
| `cloud` | removed layer | `august`, `loqed`, `mobile_app`, `monzo`, `netatmo`, `overseerr`, `owntracks`, `plaato`, `rachio`, `switchbot_cloud`, `toon`, `watts`, `withings`, `yale` |
| `backup` | removed layer | `aws_s3`, `azure_storage`, `backblaze_b2`, `cloudflare_r2`, `dropbox`, `google_drive`, `idrive_e2`, `onedrive`, `onedrive_for_business`, `sftp_storage`, `synology_dsm`, `webdav` |
| `onboarding` | removed layer | `awair`, `bthome`, `cast`, `elgato`, `homewizard`, `technove`, `thread`, `wiz`, `wled`, `xiaomi_ble`, `yeelight`, `zha` |
| `hassio` | removed layer | `esphome`, `hardkernel`, `homeassistant_alerts`, `homeassistant_green`, `homeassistant_hardware`, `homeassistant_yellow`, `otbr`, `raspberry_pi`, `zwave_js` |
| `file_upload` | removed layer | `google_cloud`, `influxdb`, `knx`, `local_calendar`, `sftp_storage`, `velbus`, `zha` |
| `homeassistant_hardware` | blocked integration | `homeassistant_connect_zbt2`, `homeassistant_green`, `homeassistant_sky_connect`, `homeassistant_yellow`, `otbr`, `raspberry_pi`, `zha` |
| `hardware` | removed layer | `hardkernel`, `homeassistant_connect_zbt2`, `homeassistant_green`, `homeassistant_sky_connect`, `homeassistant_yellow`, `raspberry_pi` |
| `input_number` | removed layer | `bayesian`, `derivative`, `filter`, `homekit`, `integration`, `min_max` |
| `ai_task` | removed layer | `anthropic`, `google_generative_ai_conversation`, `ollama`, `open_router`, `openai_conversation` |
| `frontend` | removed layer | `insteon`, `knx`, `lcn`, `mobile_app`, `panel_custom` |
| `stt` | removed layer | `elevenlabs`, `google_cloud`, `google_generative_ai_conversation`, `openai_conversation`, `wyoming` |
| `panel_custom` | blocked integration | `dynalite`, `insteon`, `knx`, `lcn` |
| `analytics` | removed layer | `esphome`, `mobile_app`, `wled` |
| `assist_pipeline` | removed layer | `esphome`, `voip`, `wyoming` |
| `assist_satellite` | removed layer | `esphome`, `voip`, `wyoming` |
| `counter` | removed layer | `derivative`, `integration`, `trend` |
| `homeassistant_yellow` | blocked integration | `otbr`, `zha` |
| `input_boolean` | removed layer | `bayesian`, `homekit` |
| `thread` | blocked integration | `homekit_controller`, `otbr` |
| `cast` | blocked integration | `plex` |
| `default_config` | removed layer | `go2rtc` |
| `homeassistant_sky_connect` | blocked integration | `zha` |
| `input_button` | removed layer | `homekit` |
| `input_select` | removed layer | `homekit` |
| `input_text` | removed layer | `bayesian` |
| `plex` | blocked integration | `sonos` |
| `sensor.recorder` | removed layer | `utility_meter` |
| `telegram_bot` | blocked integration | `telegram` |
| `wake_word` | removed layer | `wyoming` |
| `zha` | blocked integration | `homeassistant_hardware` |

`utility_meter` imports `reset_detected` from `sensor/recorder.py`, which left
with Recorder (#28); the domain-level walk cannot see a removed module inside
a retained component, and the import check of the restore did.

38 virtual integrations point at one of those, and wait for their target:

- `esphome`: `apollo_automation`, `iotorero`, `konnected_esphome`
- `homewizard`: `eastron`
- `netatmo`: `bticino`, `bubendorff`, `home_plus_control`, `legrand`, `smarther`
- `opower`: `aep_ohio`, `aep_texas`, `appalachianpower`, `atlanticcityelectric`, `bge`, `burbank_water_and_power`, `coautilities`, `comed`, `coned`, `delmarva`, `duquesne_light`, `evergy`, `indianamichiganpower`, `kentuckypower`, `oru_opower`, `peco_opower`, `pepco`, `pge`, `pse`, `psoklahoma`, `scl`, `smud`, `swepco`
- `sonos`: `symfonisk`
- `tplink`: `tplink_tapo`
- `whirlpool`: `bauknecht`, `maytag`
- `wyoming`: `piper`, `whisper`

Bringing one back is a decoupling change of the #25 kind: patch the import of
the removed layer out of the integration, or restore a layer that turns out to
serve devices rather than people, as `media_source` did. The gate then
accepts it, and the catalog job runs its suite.
