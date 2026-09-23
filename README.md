# ha-lite

A headless, deliberately reduced device runtime exploring how much of Home Assistant's integration knowledge can be retained without carrying the complete Home Assistant product.

> Early architecture and reduction experiment. Not yet a usable Home Assistant distribution.

## Why this exists

Home Assistant Core contains two things that are valuable for very different reasons:

1. an unusually broad, battle-tested integration runtime for real devices and services;
2. the backend of a complete end-user home-automation product.

ha-lite explores how small and understandable the first can become when the second is deliberately removed.

The goal is **not** to run normal Home Assistant with its UI disabled. Code outside the target runtime is physically removed when practical, so it no longer contributes dependencies, coupling, maintenance surface, searches, or agent context.

One important accounting detail: the browser application itself lives primarily in the separate `home-assistant-frontend` project/package. Removing Core's `frontend` and `lovelace` components therefore removes product coupling but does **not** by itself delete the enormous JavaScript/TypeScript frontend from this repository — that code was never here. The large Core reduction comes from the combination of product subsystems and, eventually, the long tail of integrations that ha-lite does not choose to carry.

## Direction

ha-lite treats Home Assistant Core as high-value source material rather than an architectural constraint. The target runtime is responsible for the physical-world boundary:

- discover and configure devices and services;
- maintain stable device and entity identities;
- observe and normalize state;
- expose capabilities and actions;
- publish events and state changes;
- persist the minimum state and configuration required for reliable operation;
- provide machine-oriented HTTP/WebSocket/webhook APIs;
- provide MCP as a first-class agent-control surface.

Decision making belongs outside the core. Automations, schedules, dashboards, scenes, voice presentation, and other product-level features are not intended to be part of the runtime unless a retained machine-facing contract proves that a smaller underlying primitive is required.

## Scope at a glance

This table describes the architectural target. **Removed** means physically absent from the tree; **Keep** means part of the retained runtime contract and protected by CI.

| Area | Direction | Current status / rationale |
| --- | --- | --- |
| Core state machine, event bus, service dispatch | **Keep** | Fundamental runtime primitives |
| Config entries and config flows | **Keep** | Headless device/integration lifecycle |
| Device/entity registries | **Keep** | Stable physical-world identity |
| Integration loader and requirements machinery | **Keep / reduce** | Needed to reuse selected HA integrations; simplification is Wave 5 (#29) |
| HTTP, auth, WebSocket API, webhooks | **Keep / reduce** | Machine-facing control and integration infrastructure |
| MCP server | **Keep** | First-class agent-control surface; protected by protocol-level CI |
| Conversation / intent / LLM substrate | **Keep / reduce** | Retain the subset required by MCP, not the voice product |
| Representative integrations (Shelly, MQTT, Matter, Hue, Fronius, Modbus) | **Keep** | Compatibility anchors while reducing the runtime |
| Miele | **Keep** | OAuth anchor: application credentials, authorization and reauth against a real integration (ADR 0017) |
| Entity-domain substrate, device-class trigger vocabulary | **Keep** | What the retained integrations implement, and the named triggers/conditions over it (ADR 0012) |
| Scenes, `person`, `group`, `zone`, `sun` | **Keep** | Device-stored state, aggregation over retained entities and solar position; none of it decides anything (ADR 0002) |
| Frontend, Lovelace, panel registration, browser launch | **Removed — Wave 1** | Backend boots and operates with the packages physically absent |
| Automation, scripts | **Removed — Wave 2** | Decision/orchestration layer belongs outside the runtime |
| Blueprints, templates, automation helpers, cloud, Alexa, Google Assistant | **Removed — Wave 3** | Automation authoring and cloud products (#19) |
| Logbook, history, energy | **Removed — Wave 3** | Human-facing history and aggregation products (#21) |
| Onboarding, default bundle, browser upload and link helpers | **Removed — Wave 3** | Replaced by a first-run command and explicit defaults (#22, #30, ADR 0016) |
| Assist / voice presentation, media browser, AI tasks | **Removed — Wave 3** | Outside the MCP closure; a headless MCP test guards the gap (#23) |
| Unselected integrations | **Removed — Wave 4** | The tree is the computed retained closure; a component outside it fails CI (#27) |
| Recorder, persistence implementation | **Decide — Wave 5** | Define the persistence contract first (#28) |

The detailed classification lives in [the scope matrix](docs/architecture/scope-matrix.md). The [roadmap](docs/architecture/roadmap.md) lists every open block with its GitHub issue.

## How large is the reduction?

A useful measurement needs to distinguish **Home Assistant Core source** from the separately distributed browser frontend.

| Metric | Before Wave 1 | Current |
| --- | ---: | ---: |
| Tracked files in repository | 27,507 | 3,202 |
| Tracked Python files | 18,497 | 2,270 |
| Product Python under `homeassistant/` | 10,028 files / 51.36 MB | 979 files / 8.75 MB |
| Python under `homeassistant/components/` | 9,814 files / 48.51 MB | 766 files / 6.03 MB |
| Top-level component domains | 1,509 | 91 |
| Python tests under `tests/` | 8,269 files / 67.45 MB | 1,094 files / 17.31 MB |

"Before Wave 1" is the upstream 2026.9.3 tree immediately before the frontend and Lovelace deletion. "Current" is this checkout; the [roadmap](docs/architecture/roadmap.md#size-checkpoints) keeps the intermediate checkpoints.

Waves 1–3 barely moved these numbers: roughly 94% of the Python bytes under `homeassistant/` were component code, and the product layers are a small part of it. Wave 4 is where the size went. The [retained closure](docs/architecture/retained-closure.md) reached 88 of 1,470 component domains, and deleting everything outside it leaves ha-lite with **17% of the upstream product Python** (8.75 of 51.36 MB), 6% of the component domains, a quarter of the test code, and 43 pinned packages in `requirements_all.txt` where there were 1,146.

Wave 5 changes persistence and configuration rather than deleting components, so these numbers should move little from here. Each wave still records its checkpoint.

`script/ha_lite_size_report.py` produces reproducible file/line/byte counts from a checkout, so the same measurement can be repeated before and after each deletion wave.

## Roadmap

| Wave | Scope | Status |
| --- | --- | --- |
| 1 | Frontend, Lovelace and browser-product bootstrap | Done |
| 2 | Automation and Script | Done |
| 3 | Remaining product layers ([#16](https://github.com/sebastian-software/ha-lite/issues/16)) | Done |
| 4 | Explicit retained integration closure ([#17](https://github.com/sebastian-software/ha-lite/issues/17)) | Done |
| 5 | Persistence, configuration and runtime composition ([#18](https://github.com/sebastian-software/ha-lite/issues/18)) | In progress |

[docs/architecture/roadmap.md](docs/architecture/roadmap.md) states each wave's entry and exit criteria and links the issue behind every open block. The architecture documents are the design source of truth; GitHub issues track execution.

## First run

There is no onboarding UI. Create the owner and a token for your client, then
start the runtime:

```bash
hass --script owner -c config create --name "Admin" --username admin
hass --script owner -c config token --client-name "mcp agent"
hass -c config
```

The generated `configuration.yaml` lists the discovery integrations it enables;
remove a line to turn one off. Everything else is configured through config
flows over the WebSocket or REST API. If the configuration cannot be loaded,
ha-lite starts in recovery mode with the API up and the reason in
`/api/error_log`. [ADR 0016](docs/adr/0016-headless-first-run-and-recovery.md)
has the details.

## What success looks like

ha-lite should remain able to discover, configure, observe and control retained devices while being substantially smaller and conceptually narrower than Home Assistant Core. In particular, headless operation is a contract rather than a launch option: frontend/Lovelace must be physically absent, while HTTP/WebSocket APIs, representative integrations and MCP continue to work.

See [the architecture overview](docs/architecture/overview.md), [scope matrix](docs/architecture/scope-matrix.md), [testing strategy](docs/architecture/testing-strategy.md), and [ADRs](docs/adr/).
