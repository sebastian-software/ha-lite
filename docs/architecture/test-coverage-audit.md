# Retained test coverage audit

## Result

The first green ha-lite baseline was useful but not complete enough to claim that every intended retained contract was directly protected.

The audit found three gaps:

1. **Core helper/runtime contracts were mostly covered indirectly** through integration tests but not directly.
2. **Several retained system components had no explicit CI suite**, including API, logging/system health, application credentials, webhooks and persistent notifications.
3. **Entity-domain contracts were exercised by integrations but not independently protected**, even though Shelly, Matter and MQTT depend on a broad set of entity base classes, service semantics, feature flags and validation rules.

The CI was expanded before Deletion Wave 1 to close those gaps, and has grown with every root the closure declared since.

## Directly protected core/helper contracts

The core-runtime job now explicitly includes tests for:

- bootstrap, core, config entries, loader and setup;
- aiohttp client helpers;
- config-flow and OAuth2-flow machinery;
- device and entity registries;
- dispatcher/event/state/service infrastructure;
- entity base/component/platform machinery;
- issue registry;
- restore-state;
- storage;
- service-info/discovery plumbing;
- system information;
- translations;
- update coordinators.

These are all APIs or implementation contracts used by retained integrations or by the intended headless runtime.

## Directly protected system components

The headless-infrastructure job now includes:

- api
- auth
- http
- websocket_api
- config
- logger
- system_log
- system_health
- application_credentials
- webhook
- persistent_notification
- homeassistant core integration
- network
- zeroconf
- bluetooth
- dhcp
- ssdp
- usb
- repairs
- diagnostics
- conversation
- mcp_server

Some of these components may later be reduced or replaced. Until that decision is explicit, their tests are intentionally conservative guards.

## Entity-domain substrate

The following generic domains are tested independently because at least one retained representative integration uses their contracts or MQTT exposes them as a supported entity type. They are exactly the `entity_domain_substrate` roots of the closure:

- alarm_control_panel
- binary_sensor
- button
- camera
- climate
- cover
- date
- datetime
- device_tracker
- event
- fan
- humidifier
- image
- infrared
- lawn_mower
- light
- lock
- media_player
- notify
- number
- scene
- select
- sensor
- siren
- switch
- tag
- text
- time
- update
- vacuum
- valve
- water_heater

This is deliberately broader than the devices currently installed. The purpose of the first phase is to preserve Home Assistant's learned integration semantics while product layers are removed.

## Device-class semantics and derived state

Two further matrices protect roots that no integration imports:

- the fifteen device-class trigger and condition providers (`air_quality`
  through `window`), ADR 0012;
- `group`, `person` and `sun`, which fold or derive state over retained
  entities, ADR 0002.

## Representative integrations

Full test directories remain required for:

- Shelly
- MQTT
- Matter
- Hue
- Fronius
- Modbus

## Still not claimed as retained

The audit does **not** promote these to retained scope merely because tests exist upstream:

- frontend / Lovelace (removed)
- automation / script / blueprint (removed)
- user schedule/timer/input helpers (removed)
- history/logbook/energy (removed)
- cloud/Nabu Casa (removed)
- onboarding and the default bundle (#22)
- Assist/voice pipelines and the media browser (removed)
- Home Assistant OS/Supervisor behavior (removed from the retained integrations)
- every unrelated device integration (#27)

Their tests disappear with the production behavior they protect. Scenes were on this list once; they are now retained substrate, because Hue and MQTT implement the `scene` entity domain.

## Remaining deliberate uncertainties

A few areas remain INVESTIGATE rather than fully committed:

- area/floor/label/category registries;
- Recorder/history persistence (#28);
- YAML configuration (#29);
- backup semantics (#28, #30);
- HomeKit controller (#27 deletes it unless it is promoted first).

Frigate was listed here as a representative higher-level integration. It is a custom integration that Home Assistant Core does not ship, so it cannot be retained in-tree; at most it becomes an external compatibility canary.

Before deleting any of these, promote them to KEEP or DELETE and adjust CI accordingly.

## Rule going forward

A component or helper classified KEEP should have at least one direct test target in ha-lite CI, not merely incidental coverage through another integration.

Integration-specific behavior should continue to run the complete upstream test directory for that retained integration.

