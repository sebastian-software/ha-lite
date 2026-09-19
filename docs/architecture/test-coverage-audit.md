# Retained test coverage audit

## Result

The first green ha-lite baseline was useful but not complete enough to claim that every intended retained contract was directly protected.

The audit found three gaps:

1. **Core helper/runtime contracts were mostly covered indirectly** through integration tests but not directly.
2. **Several retained system components had no explicit CI suite**, including API, logging/system health, application credentials, webhooks and persistent notifications.
3. **Entity-domain contracts were exercised by integrations but not independently protected**, even though Shelly, Matter and MQTT depend on a broad set of entity base classes, service semantics, feature flags and validation rules.

The CI has been expanded before Deletion Wave 1 to close those gaps.

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

Some of these components may later be reduced or replaced. Until that decision is explicit, their tests are intentionally conservative guards.

## Entity-domain substrate

The following generic domains are now tested independently because at least one retained representative integration uses their contracts or MQTT exposes them as a supported entity type:

- alarm_control_panel
- binary_sensor
- button
- camera
- climate
- cover
- date
- datetime
- event
- fan
- image
- light
- lock
- media_player
- notify
- number
- select
- sensor
- siren
- switch
- text
- time
- update
- vacuum
- valve
- water_heater

This is deliberately broader than the devices currently installed. The purpose of the first phase is to preserve Home Assistant's learned integration semantics while product layers are removed.

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

- frontend / Lovelace
- automation / script / blueprint
- scenes
- user schedule/timer helpers
- history/logbook/energy
- cloud/Nabu Casa
- Assist/voice pipelines
- Home Assistant OS/Supervisor behavior
- every unrelated device integration

Their tests can disappear when their production behavior is intentionally deleted.

## Remaining deliberate uncertainties

A few areas remain INVESTIGATE rather than fully committed:

- area/floor/label/category registries;
- Recorder/history persistence;
- YAML configuration;
- backup semantics;
- HomeKit controller;
- Frigate as a representative higher-level integration.

Before deleting any of these, promote them to KEEP or DELETE and adjust CI accordingly.

## Rule going forward

A component or helper classified KEEP should have at least one direct test target in ha-lite CI, not merely incidental coverage through another integration.

Integration-specific behavior should continue to run the complete upstream test directory for that retained integration.

