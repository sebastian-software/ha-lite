# Initial Keep / Delete / Investigate matrix

## Status and method

This is the first architectural classification, **not yet a proven deletion list**. Before deletion, each item must be checked against both Home Assistant integration manifests and actual Python imports.

Guiding rule: keep machinery required to discover, configure, identify, observe and control devices; remove product behavior and presentation.

| Area / HA component | Initial | Rationale / next check |
|---|---|---|
| Core event bus / state machine / service-action dispatch | KEEP | Fundamental physical-world runtime primitives. |
| Config entries + config flows | KEEP | Setup, reauth and reconfiguration are backend lifecycle concerns. |
| Device registry | KEEP | Stable device identity and relationships. |
| Entity registry | KEEP | Stable exposed endpoint identity. |
| Area/floor/label registries | INVESTIGATE | Useful metadata; may belong above core. |
| Integration loader / setup / requirements | KEEP | Required while executing HA integrations. Simplify later. |
| Repairs/issues infrastructure | KEEP / REDUCE | Failures must remain machine-readable; UI presentation goes. |
| Diagnostics | KEEP / REDUCE | Operationally useful; remove presentation assumptions. |
| Auth | KEEP / REDUCE | Network API requires explicit security. |
| HTTP server | KEEP initially | Required by integrations/config flows and practical API transport. |
| WebSocket API | KEEP / REDUCE | Good initial event/state/action transport; later define ha-lite contract. |
| REST API | INVESTIGATE | Retain only where useful after API contract is defined. |
| frontend | **REMOVED** | Outside headless core; physically removed in Wave 1 after bootstrap/config decoupling. |
| lovelace | DELETE | Dashboard product surface. |
| UI panels / panel registration | DELETE | Presentation concern; decouple backend config first. |
| onboarding | DELETE / REPLACE | Replace product onboarding with API/CLI bootstrap. |
| automation | DELETE | Decision engine belongs outside core. |
| script | DELETE | Behavioral orchestration belongs outside core. |
| blueprint | DELETE | Automation authoring/distribution. |
| scene | INVESTIGATE → likely DELETE | Reconsider generic batch-command primitive separately. |
| schedule | DELETE | External decision/scheduling layer. |
| timer | DELETE | Primarily automation state; verify dependencies. |
| counter | DELETE | Automation helper state. |
| input_boolean / input_button | DELETE | Virtual automation/UI helpers. |
| input_datetime / input_number | DELETE | Virtual automation/UI helpers. |
| input_select / input_text | DELETE | Virtual automation/UI helpers. |
| group | INVESTIGATE | Generic grouping may be useful above core. |
| person | DELETE initially | Derived product model, not physical device runtime. |
| zone | DELETE initially | Location/automation behavior; revisit only if required. |
| sun | DELETE | Derived automation input. |
| default_config | DELETE | Product bundle conflicts with explicit minimal composition. |
| config | KEEP / REDUCE | Backend configuration useful; remove frontend/panel coupling. |
| system_health | KEEP / REDUCE | Headless operations need health data. |
| logger | KEEP | Operational infrastructure. |
| logbook | DELETE | Human-facing historical narrative. |
| history | DELETE | Human-facing history product; raw history reconsider separately. |
| recorder | INVESTIGATE | Current persistence/history machinery; candidate for replacement. |
| long-term statistics | DELETE initially | Product analytics/history concern. |
| energy | DELETE | Product/domain aggregation, not device boundary. |
| map | DELETE | UI/product feature. |
| file_upload | DELETE initially | UI/product support unless an integration proves need. |
| backup | INVESTIGATE / REPLACE | Need backup semantics, not necessarily HA implementation. |
| cloud / Nabu Casa | DELETE | Product/cloud service outside scope. |
| conversation / intent / LLM API substrate | KEEP / REDUCE | Required by the official MCP server and useful as a machine-control contract; retain headless primitives, remove presentation/voice-product assumptions separately. |
| MCP server (`mcp_server`) | KEEP | First-class agent-control surface. Must remain usable without frontend/Lovelace and is protected by CI. |
| STT / TTS / voice presentation | DELETE / INVESTIGATE | Voice product surface is not retained merely because Conversation/MCP is retained; reassess concrete runtime dependencies before deletion. |
| media source/browser | DELETE initially | Product feature; device media controls can remain. |
| bluetooth | KEEP | Discovery/transport for physical integrations. |
| dhcp | KEEP | Discovery infrastructure. |
| ssdp | KEEP | Discovery infrastructure. |
| zeroconf | KEEP | Discovery infrastructure. |
| usb | KEEP | Discovery infrastructure for local adapters. |
| network | KEEP / REDUCE | Shared integration infrastructure. |
| webhook | KEEP / INVESTIGATE | Some integrations require inbound events. |
| OAuth2 helpers/application credentials | KEEP | Required for cloud integrations and reauth. |
| MQTT | KEEP | Representative protocol/integration substrate. |
| Shelly | KEEP | Primary representative local-device integration. |
| Matter + Matter server boundary | KEEP | Modern protocol; external helper process is acceptable. |
| Hue | KEEP initially | Representative bridge-based local integration. |
| Fronius | KEEP initially | Representative local energy-device integration; energy UI not needed. |
| HomeKit controller/device | INVESTIGATE | Useful protocol; measure dependency footprint. |
| HomeKit bridge/export | DELETE initially | Output/product compatibility unless explicitly needed. |
| Frigate | KEEP as test candidate | Useful MQTT/event/media stress case; baseline status TBD. |
| YAML configuration | INVESTIGATE | Config entries likely primary target. |
| Dynamic pip requirement installation | INVESTIGATE / REPLACE | Controlled distribution may prefer pre-resolved dependencies. |
| Supervisor | DELETE / OUT OF SCOPE | Separate runtime-management product. |
| Home Assistant OS | DELETE / OUT OF SCOPE | Appliance OS not target. |
| Docker/container requirement | DELETE as requirement | Run as normal service; containers may remain optional packaging. |

## First dependency closure

Calculate transitive runtime requirements for Shelly, MQTT, Matter, Hue and Fronius. Then add one OAuth/cloud integration to exercise generic configuration and reauthentication machinery.

## Deletion waves

1. Frontend, Lovelace, panels and UI-only support.
2. Automation, scripts, blueprints and automation helpers.
3. Product features: logbook/history UI, energy, map, voice presentation and cloud. Preserve the Conversation/LLM subset required by MCP.
4. Unselected integrations, after representative dependency closure is generated.
5. Persistence/configuration simplification only after the reduced runtime boots and representative integrations pass lifecycle tests.
