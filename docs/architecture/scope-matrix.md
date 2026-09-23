# Keep / Delete / Investigate matrix

## Status and method

This matrix is the design intent, **not a deletion list**. Before deletion, each item is checked against both Home Assistant integration manifests and actual Python imports.

That check is automated: `script/ha_lite_closure.py` computes the retained closure from both graphs, and [retained-closure.md](retained-closure.md) records what it currently says. The matrix records intent; the closure is the evidence (ADR 0010).

**REMOVED** means physically absent from the tree. A row that still has work to do names the issue that carries it; [roadmap.md](roadmap.md) groups those issues by wave.

Guiding rule: keep machinery required to discover, configure, identify, observe and control devices; remove product behavior and presentation.

| Area / HA component | Initial | Rationale / next check |
|---|---|---|
| Core event bus / state machine / service-action dispatch | KEEP | Fundamental physical-world runtime primitives. |
| Config entries + config flows | KEEP | Setup, reauth and reconfiguration are backend lifecycle concerns. |
| Device registry | KEEP | Stable device identity and relationships. |
| Entity registry | KEEP | Stable exposed endpoint identity. |
| Area/floor/label registries | INVESTIGATE | Useful metadata; may belong above core. |
| Integration loader / setup / requirements | KEEP | Required while executing HA integrations. Simplify in #29. |
| Repairs/issues infrastructure | KEEP / REDUCE | Failures must remain machine-readable; UI presentation goes. |
| recovery_mode | **KEEP (root)** | Set up by name when configuration fails; with it, recovery serves the API and reports why it started (ADR 0016). |
| Diagnostics | KEEP / REDUCE | Operationally useful; remove presentation assumptions. |
| Auth | KEEP / REDUCE | Network API requires explicit security. |
| HTTP server | KEEP initially | Required by integrations/config flows and practical API transport. |
| WebSocket API | KEEP / REDUCE | Good initial event/state/action transport; later define ha-lite contract. |
| REST API | INVESTIGATE | Retain only where useful after API contract is defined. |
| frontend | **REMOVED** | Outside headless core; physically removed in Wave 1 after bootstrap/config decoupling. |
| lovelace | **REMOVED** | Dashboard product surface; physically removed in Wave 1. |
| UI panels / panel registration | **REMOVED** | Registration lived in `frontend` and left with it in Wave 1; `config` no longer registers a panel. `panel_custom` and the integrations that still call it are outside the closure and leave in Wave 4 (#27). |
| onboarding | **REMOVED** | Replaced by `hass --script owner` for the first user and tokens, and the existing config APIs for everything else (#22, #30, ADR 0016). |
| automation | **REMOVED** | Decision engine belongs outside core; physically removed in Wave 2. |
| script | **REMOVED** | Behavioral orchestration belongs outside core; physically removed in Wave 2. |
| blueprint | **REMOVED** | Automation authoring/distribution; physically removed in Wave 3 together with Template, its only importer. |
| scene | **KEEP** | Entity domain implemented by `hue/scene.py` and `mqtt/scene.py`. A Hue scene lives on the bridge, so this is device state, not automation semantics. |
| schedule | **REMOVED** | External decision/scheduling layer; physically removed in Wave 3. |
| timer | **REMOVED** | Automation state; physically removed in Wave 3. Runtime scheduling primitives such as `async_track_time_interval` are retained. |
| counter | **REMOVED** | Automation helper state; physically removed in Wave 3. |
| input_boolean / input_button | **REMOVED** | Virtual helpers; physically removed in Wave 3 after decoupling the switch/button trigger and condition platforms. |
| input_datetime / input_number | **REMOVED** | Virtual helpers; physically removed in Wave 3. The time trigger now accepts timestamp sensors only. |
| input_select / input_text | **REMOVED** | Virtual helpers; physically removed in Wave 3 after decoupling the select/text trigger and condition platforms. |
| group | **KEEP (root)** | Folds several entities of one domain into one — several lamps, several blinds, the mean of several sensors. All twelve of its platforms target retained entity domains. Nothing imports it, so it is a root. Its `config_flow` is backend setup, which this matrix already keeps. |
| Device-class trigger/condition providers | **KEEP (roots)** | `air_quality`, `battery`, `door`, `doorbell`, `garage_door`, `gate`, `humidity`, `illuminance`, `moisture`, `motion`, `occupancy`, `power`, `temperature`, `vibration`, `window`. The named vocabulary over entity device classes; `binary_sensor` and `sensor` ship none of their own. ADR 0012. |
| device_tracker | **KEEP** | Entity domain implemented by `mqtt/device_tracker.py`. DHCP discovery also watches it, but that is not what holds it. |
| image_upload | **REMOVED** | Avatar storage for `person`; physically removed in Wave 3 after dropping the manifest dependency. |
| weather | **KEEP (root)** | Entity-domain substrate. The temperature and humidity triggers and conditions declare a `DomainSpec` over weather entities; keeping the domain leaves that vocabulary as upstream ships it, where removing it meant editing both platforms and 99 upstream test references (ADR 0012, ADR 0014). No retained integration provides the platform today. |
| person | **KEEP (root)** | The aggregation layer over `device_tracker`: several trackers per human folded into one presence answer with source selection, plus `in_zones`. Logical grouping over retained substrate, not a product surface. Its `image_upload` dependency was only the avatar and is gone. |
| zone | **KEEP** | Declared dependency in `device_tracker/manifest.json` and imported from its `entity.py` and `legacy.py`. Cannot leave while `device_tracker` stays. |
| sun | **KEEP (root)** | Solar position from the configured coordinates and the clock: elevation, azimuth, and the next dawn/dusk/noon/midnight/rising/setting. `astral` and `helpers/sun.py` are core already, so this only exposes what the core computes anyway. Fronius makes it device-relevant — a PV site's yield follows solar elevation. Nothing imports it, so it is a root. |
| default_config | **REMOVED** | Bootstrap's defaults are the always-on runtime; discovery is listed in the generated `configuration.yaml` instead (ADR 0016). |
| config | KEEP / REDUCE | Backend configuration useful; remove frontend/panel coupling. |
| system_health | KEEP / REDUCE | Headless operations need health data. |
| analytics, labs | **REMOVED** | Usage reporting to Home Assistant and its preview-feature flags (#22). |
| brands, hardware | **REMOVED** | Brand-image proxy and hardware-status panel for the frontend (#22). |
| logger | KEEP | Operational infrastructure. |
| logbook | **REMOVED** | Human-facing historical narrative; physically removed in Wave 3 together with its per-integration describe platforms. |
| history | **REMOVED** | Human-facing history product; physically removed in Wave 3. Raw state history left with Recorder in Wave 5 (ADR 0018). |
| recorder | **REMOVED** | States, events and statistics in SQLite. Never a default, and nothing retained required it; removed in Wave 5 with `sensor`'s statistics platform and SQLAlchemy. Clients that want history subscribe and keep it (#28, ADR 0018). |
| long-term statistics | **REMOVED** | Left with Recorder (#28, ADR 0018). |
| energy | **REMOVED** | Product/domain aggregation; physically removed in Wave 3 after decoupling Analytics reporting. |
| map | **ABSENT** | Not present in the imported 2026.9.3 tree; the map view is a frontend dashboard. |
| map_tiles, my, search | **REMOVED** | The OpenStreetMap tile proxy behind the frontend's base map, the `my.home-assistant.io` redirect service, and the frontend's related-items search (#22). Without `my`, the OAuth2 flow helper redirects to the instance's own callback URL, which is what OAuth applications register (#26). |
| file_upload | **REMOVED** | MQTT takes certificate material as PEM text since #25 (#22). |
| backup | **REMOVED** | Deleted with its storage agents in Wave 4 (#27). A backup of ha-lite is a copy of the configuration directory taken while it is stopped (ADR 0018). |
| cloud / Nabu Casa | **REMOVED** | Product/cloud service; physically removed in Wave 3 with Alexa and Google Assistant, which only existed to serve it. |
| conversation / intent / LLM API substrate | KEEP / REDUCE | Required by the official MCP server and useful as a machine-control contract; retain headless primitives, remove presentation/voice-product assumptions separately. |
| MCP server (`mcp_server`) | KEEP | First-class agent-control surface. Must remain usable without frontend/Lovelace and is protected by CI. |
| STT / TTS / voice presentation | **REMOVED** | `assist_pipeline`, `assist_satellite`, `stt`, `tts` and `wake_word` were outside the `mcp_server` closure; physically removed in Wave 3 (#23). `tests/ha_lite/test_mcp_headless.py` keeps MCP working without them. |
| media source/browser | **REMOVED** | Product feature; device media controls remain in `media_player`. Reached only through the `camera` and `image` `media_source.py` adapters, which left with it (#23). |
| ai_task | **REMOVED** | LLM product surface, set up only because bootstrap defaults to every entity platform. No retained integration provides it; agents use MCP (#23). |
| bluetooth | KEEP | Discovery/transport for physical integrations. |
| dhcp | KEEP | Discovery infrastructure. |
| ssdp | KEEP | Discovery infrastructure. |
| zeroconf | KEEP | Discovery infrastructure. |
| usb | KEEP | Discovery infrastructure for local adapters. |
| network | KEEP / REDUCE | Shared integration infrastructure. |
| webhook | KEEP / INVESTIGATE | Some integrations require inbound events. |
| OAuth2 helpers/application credentials | KEEP | Required for cloud integrations and reauth. Miele exercises them in CI as the OAuth lifecycle anchor (#26, ADR 0017). |
| Miele | KEEP (anchor) | Application credentials, OAuth2 authorize/callback/token, reauth and reconfigure against a real integration. Kept for what its tests exercise, not as a promise to retain cloud integrations (ADR 0017). |
| MQTT | KEEP | Representative protocol/integration substrate. |
| Shelly | KEEP | Primary representative local-device integration. |
| Matter + Matter server boundary | KEEP | Modern protocol; the Matter Server runs as an external process, configured by URL. The add-on lifecycle is gone (#25). |
| Hue | KEEP initially | Representative bridge-based local integration. |
| Fronius | KEEP initially | Representative local energy-device integration; energy UI not needed. |
| HomeKit controller/device | **REMOVED** | Useful protocol, but not promoted: Matter covers the same local-device ground and is retained. Deleted by reachability in Wave 4 (#27); re-adding it means declaring it a root with a CI job. |
| HomeKit bridge/export | **REMOVED** | Output/product compatibility. Deleted in Wave 4 (#27). |
| demo, kitchen_sink | **KEEP (test fixtures)** | Simulated devices that retained upstream test suites set up by name — `demo` behind the `media_player`, `camera`, `group` and config-entry tests, `kitchen_sink` behind `group`'s lock tests. Their platforms for domains ha-lite does not retain are pruned. Roots with a CI job, not runtime (#27). |
| Frigate | OUT OF TREE | Useful MQTT/event/media stress case, but a custom integration that Home Assistant Core does not ship. A compatibility canary at most, like `ha-mcp`. |
| YAML configuration | **KEEP** | Instance settings (`homeassistant:`, `http:`, `logger:`, discovery) and declarative integration configuration with no config flow — Modbus register maps, MQTT YAML entities, `group`/`person`/`zone`/`scene`. Config entries stay primary; `tests/test_config.py` is in CI (#29, ADR 0019). |
| Dynamic pip requirement installation | **KEEP** for custom integrations | The closure's requirements ship with the distribution (`requirements_all.txt`, 40 packages, validated in CI), so retained integrations install nothing at runtime. `--skip-pip` forbids it entirely (#29, ADR 0019). |
| Supervisor | DELETE / OUT OF SCOPE | Separate runtime-management product. No retained code reaches `hassio` since #25, and bootstrap no longer sets it up under `SUPERVISOR` (ADR 0016); deleted with the integration long tail in Wave 4 (#27). |
| Home Assistant OS | DELETE / OUT OF SCOPE | Appliance OS not target. |
| Docker/container requirement | DELETE as requirement | Run as normal service; containers may remain optional packaging. |

## First dependency closure

The transitive runtime requirements of Shelly, MQTT, Matter, Hue, Fronius and Modbus are computed by `script/ha_lite_closure.py` and gated in CI (#24). Miele is the seventh root: an OAuth integration that exercises the generic authorization and reauthentication machinery (#26, ADR 0017).

## Deletion waves

1. Frontend, Lovelace, panels and UI-only support. **Done.**
2. Automation and scripts. **Done.**
3. Product features: blueprints and automation helpers, logbook/history, energy, cloud, onboarding and the default bundle, voice presentation. Preserve the Conversation/LLM subset required by MCP. **Done.**
4. Unselected integrations, deleted by reachability from the computed closure. **Done:** the tree is the closure, and a component outside it fails CI.
5. Persistence/configuration simplification only after the reduced runtime boots and representative integrations pass lifecycle tests.

Entry and exit criteria for each wave, and the issue behind every open block, are in [roadmap.md](roadmap.md).
