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
**dangling**, whatever the edge's strength. That includes a manifest's
`after_dependencies`, although it is only an ordering hint. With pip allowed,
setting up a built-in integration resolves its after dependencies as well, and
one that is not there fails the setup with `IntegrationNotFound`.

For the catalog this is the entry condition. An integration that still imports
a removed product layer cannot load, so it stays out of the tree until it is
decoupled. An import of a declared compat module is satisfied: the module is
there, it is just not an integration. For the same reason a manifest entry on a
compat module is not: the loader cannot resolve it.

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
- **undeclared compat** and **stale compat** — a file directly under
  `components/` that is not listed under `compat_modules` in the config, or
  a listed one that is gone. See "Compat modules" below.

A catalog member is not a finding. It needs no root and no reviewed entry, and
the `catalog` CI job runs its suite.

## Current state

| Metric | Count |
|---|---|
| Component domains in tree | 1,370 |
| Declared roots | 90 |
| Retained closure | 98 |
| Catalog | 1,272 |

Of the 8 transitively required domains, 7 are `retained` and 1 is an `adapter`.
`recorder` was one more until #28 removed it (ADR 0018). The tree count
includes 111 virtual integrations, which are a manifest pointing at another
integration and carry no code. The ten compat modules are files, not
domains, and are not counted.

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
back 1,218 of them, and `media_source`, which Wave 3 had removed with the
voice stack, came back beside them. `trace` passed the test as well but went
back out as an excluded layer: it records and debugs automations and scripts,
which ha-lite does not run.

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

Four restored manifests listed a missing domain in `after_dependencies`:
`bluetooth_adapters` (`esphome`) and `litellm`, `llama_cpp` and
`ovhcloud_ai_endpoints` (`assist_pipeline`). hassfest rejects such entries,
and with pip allowed they would fail the setup. Those entries are removed. Brand files keep only the integrations in
the tree, and a brand left with fewer than two is removed, as hassfest
requires.

### Compat modules

Many of the integrations that stayed out imported a removed layer only to ask
it one question:

- thirteen asked `automation`, most of them `script` as well, which
  automations and scripts use an entity or device, to decide whether a
  deprecation notice lists them;
- `emulated_hue` and `telegram_bot` needed only the `script` domain name;
- eleven config flows asked `onboarding` whether the browser wizard is still
  running, to add a discovered device without asking.

Three compat modules answer those questions; a second round below added
eight more, and account linking later made one of those, `cloud`, an
integration again. Each is a single file directly under `homeassistant/components/`,
without a manifest, so it is not an integration and cannot be set up
(ADR 0020):

| Module | Provides | Answer in ha-lite |
|---|---|---|
| `automation.py` | `DOMAIN`, `automations_with_entity`, `automations_with_device` | No automation references anything |
| `script.py` | `DOMAIN`, `CONF_MODE`, `CONF_SEQUENCE`, `scripts_with_entity` | No script references anything |
| `onboarding.py` | `DOMAIN`, `async_is_onboarded`, `async_is_user_onboarded` | Onboarded |

Each answer is the one upstream gives when the product integration is not
loaded. So these integrations behave as they do on a Home Assistant without
automations or a wizard: a deprecation notice lists no automations, and a
discovered device waits for the user's confirmation. `script.py` was there
before as a domain marker, and it gained `scripts_with_entity`. The closure
config lists the modules under `compat_modules`, and `retained-closure.json`
records which components import each one.

In tests, the lookups answer from the automation harness instead
(`tests/components/__init__.py`), so a deprecation test finds the automations
and scripts it set up.

The modules brought back 30 integrations and the 5 virtual integrations that
point at them:

- **Through `automation` and `script`:** `airvisual`, `elkm1`,
  `emulated_hue`, `jvc_projector`, `lg_thinq`, `opensensemap`, `ring`,
  `roborock`, `smartthings`, `telegram_bot`, `tplink`, `unifiprotect`, `v2c`,
  `victron_gx`, `whirlpool`.
- **Through `onboarding`:** `awair`, `bthome`, `cast`, `elgato`, `homewizard`,
  `technove`, `thread`, `wiz`, `wled`, `xiaomi_ble`, `yeelight`.
- **With one of the above, which they depend on:**
  - `homekit_controller`, on `thread`;
  - `plex`, on `cast`;
  - `sonos`, on `plex`;
  - `telegram`, on `telegram_bot`.
- **Virtual:** `bauknecht`, `eastron`, `maytag`, `symfonisk`, `tplink_tapo`.

Around them, these files changed:

- WLED's `analytics.py` platform and its test are removed. Only the removed
  `analytics` integration loads that platform, so it leaves with that layer,
  as logbook's describe platforms did.
- Cast's manifest drops `tts` from `after_dependencies`, which hassfest
  rejects for domains that are not in the tree. It dropped `cloud` too, until
  account linking brought `cloud` back (below).
- `unifi_discovery` maps Protect consoles to `unifiprotect` again, as upstream
  does.

These upstream tests changed:

- Cast's tests for failed casts no longer set up TTS, which only gave them a
  URL to cast.
- Cast's test of the Home Assistant Cloud URL is removed.
- UniFi Protect's `test_recorder.py` is removed.

#### The second round

The same kind of question held back 17 more integrations:

- ten ask `cloud` whether Home Assistant Cloud can give them a public webhook
  URL: `loqed`, `monzo`, `netatmo`, `overseerr`, `owntracks`, `plaato`,
  `rachio`, `switchbot_cloud`, `toon` and `withings`;
- HomeKit Bridge and five helpers — `bayesian`, `derivative`, `integration`,
  `min_max` and `trend` — name the `input_*` and `counter` domains among the
  ones they support, and HomeKit also uses their attribute and service names;
- go2rtc checks whether `default_config:` is configured.

| Module | Provides | Answer in ha-lite |
|---|---|---|
| `cloud.py`, now `cloud/__init__.py` | `DOMAIN`, the `CloudNotAvailable`/`CloudNotConnected` errors, `CloudConnectionState` and its signal, the subscription and connection checks, the cloudhook functions and the change listeners | No subscription, no connection; creating a cloudhook raises `CloudNotConnected` |
| `default_config.py` | `DOMAIN` | Never configured, so go2rtc starts only when `go2rtc:` is |
| `counter.py`, `input_boolean.py`, `input_text.py` | `DOMAIN` | Selectors that name them find nothing |
| `input_button.py` | `DOMAIN`, `SERVICE_PRESS` | As above |
| `input_number.py` | `DOMAIN`, `ATTR_VALUE`, `CONF_MIN`, `CONF_MAX`, `CONF_STEP`, `SERVICE_SET_VALUE` | As above |
| `input_select.py` | `DOMAIN`, `SERVICE_SELECT_OPTION` | As above |

The integrations behave as they do on a Home Assistant without a Nabu Casa
subscription. Netatmo, Withings, OwnTracks and the others register their local
webhook URL, which the device or service must be able to reach. Netatmo signs in
with the user's own application credentials. go2rtc, which gives camera
streams WebRTC, starts when `go2rtc:` is configured. In the container image,
which ships the go2rtc binary, that is all it needs; elsewhere it needs a `url:`
of a running go2rtc server.

The restore brought back those 17 integrations and Netatmo's five virtual
integrations, `bticino`, `bubendorff`, `home_plus_control`, `legrand` and
`smarther`.

Around them, these files changed:

- `derivative`, `integration` and `trend` drop `counter` from
  `after_dependencies`. A compat module is not an integration, so the entry
  would fail their setup. The ten that dropped `cloud` name it again since
  account linking made it an integration.
- hassfest's import check (`script/hassfest/dependencies.py`) accepts imports
  of compat modules without a manifest entry, which it otherwise requires.
- The closure gate reports a manifest entry on a missing domain or on a compat
  module as dangling. It used to let `after_dependencies` pass, on the wrong
  assumption that the loader ignores them.
- `tests/helpers/helper_harness.py` drops its stand-ins for the domain names of
  `input_number`, `input_select` and `counter`, which the compat modules now
  provide.
- `tests/ha_lite/test_mcp_headless.py` no longer lists `cloud` among the
  products that cannot be imported. `tests/ha_lite/test_compat_modules.py`
  checks every compat module instead: a plain module, without a manifest, that
  the loader does not resolve to an integration.

These upstream tests changed:

- OwnTracks' two tests and Plaato's two tests that set up the real cloud
  integration and patch `hass_nabucasa` are removed. The tests of the local
  webhook path remain.
- `test_todo_add_item_fr` in `conversation` waits for `todo`'s intent
  platform, which loads in the background, before it speaks to it. It failed
  when that import was slow.

Synology DSM stays out after all. Besides its backup-agent platform, its config
flow asks for a backup share, and it raises a repair when none is set, for a
feature ha-lite does not have. Removing that takes edits in several of its
files.

#### Account linking

August, Yale and Watts waited for `cloud` as a dependency. They sign in with
OAuth, and their vendors give client credentials only to Nabu Casa. Nabu
Casa's account link server holds the credentials and runs the sign-in:

1. The config flow asks the server for an authorize URL, over a websocket.
2. The user signs in at the vendor, which redirects to the server, not to the
   instance.
3. The server sends the tokens back over the websocket.
4. Tokens are refreshed through the server as well.

None of this needs a Home Assistant Cloud account: hass_nabucasa's
`account_link` module sends no credentials. The browser never has to reach
the instance either, which suits a headless runtime.

`cloud` is back as an integration reduced to account linking:

| File | Source | Content |
|---|---|---|
| `account_link.py` | upstream, unchanged | Offers the account link server as an OAuth2 implementation for every domain the server lists |
| `__init__.py` | ha-lite | Sets account linking up, and gives the compat module's answers: no login, no subscription, no connection, no cloudhook |
| `const.py` | ha-lite | `DOMAIN`, and `DATA_CLOUD`, where upstream keeps its hass_nabucasa `Cloud` |
| `manifest.json` | ha-lite | No dependencies. Its one requirement, `hass-nabucasa`, is a core requirement already, for `http` |

Upstream builds a hass_nabucasa `Cloud`, and with it remote access, voice,
Alexa and Google Assistant. hass_nabucasa's account link functions read two
of its attributes: the client's web session and the server's host name. So
ha-lite stores an object that has only those two.

Around it, these files changed:

- The closure config drops `cloud` from the excluded layers and from the
  compat modules. It is a catalog integration now.
- The ten manifests that dropped `cloud`, and Cast's, name it in
  `after_dependencies` again, as upstream does.
- The brands `august`, `yale` and `yale_august` are upstream's again.
- `tests/components/cloud/__init__.py` has upstream's `mock_cloud` helper,
  without the hass_nabucasa `Cloud` it also initialized. Catalog tests call it
  before they patch the cloud functions to reach their cloudhook code.
- `tests/components/cloud/` runs upstream's `test_account_link.py`, which
  patches hass_nabucasa's functions. ha-lite's `test_init.py` runs them
  against the stand-in instead, and covers the compat module's answers.

What an operator should know:

- `cloud:` in the configuration sets up account linking for integrations that
  list `cloud` only in `after_dependencies`. A config entry that signed in
  through account linking in Home Assistant needs it to refresh its token.
  Options carried over from Home Assistant, such as `alexa:`, are logged and
  ignored.
- A `cloud` config entry carried over from a Home Assistant that was logged in
  to Nabu Casa fails to load with an error, because ha-lite's `cloud` has no
  config flow. Account linking works regardless; the entry can be deleted.
- The account link server is Nabu Casa's service for Home Assistant. If Nabu
  Casa restricts it, these integrations lose their sign-in. ha-lite cannot run
  a server of its own, because the vendor credentials belong to Nabu Casa.

### What is still out

70 integrations are still out, and 28 virtual integrations point at them. They
fall into two groups.

**Out by design (56).** Their purpose is a product layer ha-lite removed, so
they leave with it:

| Group | Integrations |
|---|---|
| Speech and AI: text-to-speech, speech-to-text, conversation agents, AI tasks (18) | `amazon_polly`, `anthropic`, `baidu`, `elevenlabs`, `fish_audio`, `google_cloud`, `google_generative_ai_conversation`, `google_translate`, `marytts`, `microsoft`, `ollama`, `open_router`, `openai_conversation`, `picotts`, `voicerss`, `voip`, `wyoming`, `yandextts` |
| History and statistics: they write to or read from Recorder's database (17) | `anglian_water`, `elvia`, `filter`, `history_stats`, `ista_ecotrend`, `mill`, `opower`, `plant`, `solaredge`, `sql`, `srp_energy`, `statistics`, `suez_water`, `tibber`, `usage_prediction`, `utility_meter`, `waterfurnace` |
| Backup agents (12) | `aws_s3`, `azure_storage`, `backblaze_b2`, `cloudflare_r2`, `dropbox`, `google_drive`, `idrive_e2`, `onedrive`, `onedrive_for_business`, `sftp_storage`, `synology_dsm`, `webdav` |
| Home Assistant's own hardware and OS (8) | `hardkernel`, `homeassistant_alerts`, `homeassistant_connect_zbt2`, `homeassistant_green`, `homeassistant_hardware`, `homeassistant_sky_connect`, `homeassistant_yellow`, `raspberry_pi` |
| Automation logic (1) | `intent_script` |

Five of these are device integrations for which the removed layer is a side
feature:

- Mill, SolarEdge, Tibber and WaterFurnace import their history into Recorder's
  statistics.
- Synology DSM has a backup-agent platform, and its config flow and a repair
  ask for a backup share (see the second round above).

Each could come back without that part, as WLED did, at the cost of edits to
its own files.

`utility_meter` imports `reset_detected` from `sensor/recorder.py`, which left
with Recorder (#28). The domain-level walk cannot see a removed module inside
a retained component; the import check of the restore did.

**Waiting for a decoupling (14).** These serve devices, and a coupling holds
them back, not their purpose:

| Needs | Integrations | What for |
|---|---|---|
| `frontend`, `analytics` | `mobile_app` | The frontend's web app manifest, and an analytics platform. The `cloud` integration answers its cloud questions, except for the remote access URL |
| `hassio`, Home Assistant hardware | `esphome`, `otbr`, `zha`, `zwave_js` | Managing the add-on that runs the server, firmware for Home Assistant's own radios. ESPHome also brings the voice satellite |
| `file_upload` | `influxdb`, `knx`, `local_calendar`, `velbus` | Uploading a certificate, keyring or file in a config flow |
| `frontend`, `panel_custom` | `dynalite`, `insteon`, `knx`, `lcn`, `panel_custom` | A configuration panel in the web UI |
| `tts` | `smtp` | Attaching generated speech to a mail |

The 28 virtual integrations wait for their target:

- `esphome`: `apollo_automation`, `iotorero`, `konnected_esphome`
- `opower`: `aep_ohio`, `aep_texas`, `appalachianpower`, `atlanticcityelectric`, `bge`, `burbank_water_and_power`, `coautilities`, `comed`, `coned`, `delmarva`, `duquesne_light`, `evergy`, `indianamichiganpower`, `kentuckypower`, `oru_opower`, `peco_opower`, `pepco`, `pge`, `pse`, `psoklahoma`, `scl`, `smud`, `swepco`
- `wyoming`: `piper`, `whisper`

An integration in the second group comes back in one of three ways:

- a decoupling change of the #25 kind, which patches the import of the removed
  layer out of the integration;
- a compat module, where the coupling is only a question;
- restoring a layer, or the part of it, that turns out to serve devices rather
  than people, as `media_source` did and account linking did for `cloud`.

The gate then accepts it, and the catalog job runs its suite.
