# Home Assistant dependency findings — 2026.9.3

## Scope

First source-level pass over Home Assistant Core **2026.9.3**, centered on the representative integrations Shelly, MQTT, Matter, Hue and Fronius.

This pass distinguishes:

- **declared dependencies** from `manifest.json`;
- **implicit dependencies** visible in Python imports;
- **product coupling** that should be patched out rather than retained;
- **platform/domain components** that look generic but are part of the integration runtime.

This is intentionally more conservative than the architectural scope matrix: it records what the current code actually needs before reduction.

## Declared integration graph

```text
Shelly
├─ bluetooth
│  └─ usb
├─ http
└─ network

MQTT
├─ file_upload
│  └─ http
├─ http
└─ after: hassio

Matter
├─ websocket_api
├─ after: bluetooth
└─ after: hassio

Fronius
└─ modbus

Hue
└─ no hard manifest dependencies
   discovery: zeroconf + HomeKit metadata
```

External libraries of particular interest:

| Integration | Library |
|---|---|
| Shelly | `aioshelly==13.32.0` |
| MQTT | `paho-mqtt==2.1.0` |
| Matter | `matter-python-client==1.4.0`, `matter-ble-proxy==0.7.1` |
| Hue | `aiohue==4.9.0` |
| Fronius | `PyFronius==0.8.2`, `fronius-modbus==0.2.0` |
| Modbus | `pymodbus==3.13.1`, `modbus-connection[tmodbus]==4.10.0`, `tmodbus==0.6.2` |

## Important finding: entity platform components are runtime API, not UI

A large part of `homeassistant/components` cannot be classified by directory name alone.

Shelly directly exposes or imports platform implementations for binary sensor, button, camera, climate, cover, event, light, media player, number, select, sensor, switch, text, update and valve.

Matter similarly imports domain components such as fan, lock, siren, valve, event, cover, update, switch, button, vacuum, light, water heater, climate, number and select.

These modules define entity contracts, device classes, feature flags, validation and service semantics. They are not merely dashboard code.

**Consequence:** the first reduction should retain the generic entity-domain substrate needed by selected integrations even if some domains are not currently used in Sebastian's house. Pruning those platforms is a later, measured optimization.

## Shelly

### Declared

`bluetooth`, `http`, `network`; discovery through Bluetooth and Zeroconf.

### Implicit/core coupling observed

- config entries and migration
- device registry
- entity registry
- issue registry / repairs
- aiohttp client helper
- update coordinators
- HTTP views and source-IP/network helpers
- Zeroconf config-flow service info
- many entity platform components

### Clean deletion opportunities

Shelly contains optional HA product adapters that should not force their parent products to remain:

- `shelly/logbook.py` depends on `logbook`; delete with logbook.
- `shelly/device_trigger.py` depends on `device_automation`; delete with HA automation/device-trigger support.

Diagnostics and repairs are different: they contain useful operational/device knowledge and should initially remain, with their presentation/API surface reduced later.

### Assessment

**Excellent anchor integration.** Its underlying device communication is already isolated in `aioshelly`, while the HA layer demonstrates exactly which runtime contracts ha-lite needs to preserve.

## MQTT

### Declared

`file_upload` and `http`; `hassio` is an after-dependency.

### Unexpected coupling

The MQTT config flow directly imports:

- `file_upload.process_uploaded_file`;
- Hass.io add-on management types;
- UI-oriented selector classes;
- constants/types from many entity platform components.

The file-upload dependency is primarily part of certificate/key configuration UX. This makes the current manifest dependency real, but not necessarily architectural.

### Reduction direction

Do **not** keep `file_upload` merely because MQTT currently declares it.

Instead, split MQTT configuration into:

1. protocol/runtime configuration;
2. certificate material input/storage;
3. Home Assistant OS add-on convenience;
4. schema/presentation metadata.

ha-lite needs (1) and (2). It does not need the HA OS add-on path. The headless API can accept certificate material or references without preserving the current browser upload product.

This is an example where a manifest dependency should be **patched away**, not transitively accepted.

## Matter

### Declared

Hard dependency on `websocket_api`; after-dependencies on `bluetooth` and `hassio`.

### Unexpected coupling

Matter imports Hass.io add-on management directly in runtime/config-flow code, and its config flow imports onboarding state. Its API is implemented on HA's WebSocket API.

This means simply deleting Supervisor/Hass.io/onboarding will break Matter even though Hass.io is only listed as an after-dependency.

### Reduction direction

Matter needs an explicit portability patch:

- preserve the Matter Server client boundary;
- preserve WebSocket functionality initially;
- make HA add-on lifecycle optional/absent;
- remove onboarding assumptions;
- configure an external Matter Server endpoint directly;
- retain Bluetooth/BLE proxy support where useful.

This is a strong validation of the ha-lite architecture: protocol service lifecycle and Home Assistant appliance management are currently mixed but separable concerns.

## Hue

Hue has no hard manifest dependencies, but this does **not** mean zero runtime coupling.

The config flow uses HA config-flow machinery, aiohttp helpers, device registry and Zeroconf service info. Pairing is a backend state machine: discovery/manual host → bridge lookup → physical link-button step → credential creation → config entry.

This is exactly the kind of flow ha-lite should preserve while exposing it through API/CLI rather than a dashboard.

The current setup also contains migration/backwards-compatibility logic for old Hue bridge identities. This is valuable learned behavior and a reason not to rewrite integrations prematurely.

## Fronius

### Declared

Hard dependency on `modbus`.

### Runtime coupling observed

- config entries
- device registry
- aiohttp client
- dispatcher
- periodic event helper
- data-update coordinators
- binary sensor/number/sensor/switch platforms

Fronius is a useful counterexample to the idea that all scheduling should disappear: its periodic rescan uses `async_track_time_interval`.

That timer is **integration lifecycle polling**, not user automation.

**Consequence:** delete user-facing `schedule`/`timer` automation products, but retain low-level runtime scheduling/timer primitives required for polling, retry, refresh and housekeeping.

## Revised classification rules

The first pass suggests five categories rather than treating all components uniformly:

1. **Core runtime — KEEP:** event bus, state, config entries, registries, loader, entity model, lifecycle scheduling, HTTP primitives.
2. **Device/protocol integrations — SELECTIVE KEEP:** Shelly, MQTT, Matter, Hue, Fronius and their transitive protocol needs.
3. **Entity-domain substrate — KEEP AS REQUIRED:** sensor, switch, light, climate, etc. These are runtime contracts.
4. **Product adapters — DELETE/PATCH:** frontend, Lovelace, logbook adapters, device automation triggers, Hass.io add-on convenience, onboarding assumptions.
5. **Presentation/config UX — REPLACE:** selectors, panels, browser file upload and similar mechanisms where the underlying configuration semantics remain useful.

## Immediate deletion candidates with high confidence

These are architectural candidates; actual deletion still needs tests/import checks:

```text
homeassistant/components/frontend/
homeassistant/components/lovelace/
homeassistant/components/automation/
homeassistant/components/script/
homeassistant/components/blueprint/
homeassistant/components/logbook/
homeassistant/components/energy/
homeassistant/components/map/
homeassistant/components/cloud/
homeassistant/components/shelly/logbook.py
homeassistant/components/shelly/device_trigger.py
```

Likely candidates after decoupling:

```text
homeassistant/components/onboarding/
homeassistant/components/file_upload/
Home Assistant OS / hassio-specific paths inside retained integrations
user-facing schedule/timer/input_* integrations
```

## Next analysis

1. Generate a repository-wide import graph for retained integrations, not only search excerpts.
2. Separate generic entity-domain substrate from integration-specific dependencies.
3. Identify bootstrap imports that make deleted product components start-critical.
4. Produce the first executable deletion wave: frontend/Lovelace plus bootstrap/config decoupling.
5. Add tests that boot the reduced runtime and exercise one Shelly config-entry lifecycle.
