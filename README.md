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

This table describes the architectural target. **Removed** means physically deleted or being deleted as part of the named wave; **Keep** means part of the retained runtime contract.

| Area | Direction | Current status / rationale |
| --- | --- | --- |
| Core state machine, event bus, service dispatch | **Keep** | Fundamental runtime primitives |
| Config entries and config flows | **Keep** | Headless device/integration lifecycle |
| Device/entity registries | **Keep** | Stable physical-world identity |
| Integration loader and requirements machinery | **Keep / reduce** | Needed to reuse selected HA integrations |
| HTTP, auth, WebSocket API, webhooks | **Keep / reduce** | Machine-facing control and integration infrastructure |
| MCP server | **Keep** | First-class agent-control surface; protected by protocol-level CI |
| Conversation / intent / LLM substrate | **Keep / reduce** | Retain the subset required by MCP, not the voice product |
| Representative integrations (Shelly, MQTT, Matter, Hue, Fronius, Modbus) | **Keep** | Compatibility anchors while reducing the runtime |
| Frontend startup/recovery/browser assumptions | **Removed** | No longer part of bootstrap semantics |
| Frontend component | **Remove — Wave 1** | Backend must boot and operate with the package physically absent |
| Lovelace/dashboard backend | **Remove — Wave 1** | Presentation/product state; MCP must continue without it |
| UI panels / panel registration | **Remove — Wave 1** | Presentation concern; backend config APIs remain |
| Automation / scripts / blueprints / helper product | **Remove — Wave 2** | Decision/orchestration layer belongs outside the runtime |
| Logbook/history product, energy, map, voice presentation, cloud | **Remove — later waves** | Product features, subject to dependency discovery |
| Unselected integrations | **Remove — later wave** | Keep an explicit useful set rather than all of Home Assistant |
| Persistence implementation | **Investigate / simplify later** | Reduce only after the retained runtime is stable |

The detailed classification lives in [the scope matrix](docs/architecture/scope-matrix.md), and the deletion sequence is documented under [architecture](docs/architecture/).

## How large is the reduction?

A useful measurement needs to distinguish **Home Assistant Core source** from the separately distributed browser frontend.

Snapshot of the repository immediately before physical Wave-1 frontend/Lovelace deletion:

| Metric | Current baseline |
| --- | ---: |
| Tracked files in repository | 27,507 |
| Tracked Python files | 18,497 |
| Product Python under `homeassistant/` | 10,028 files / 51.36 MB |
| Python under `homeassistant/components/` | 9,814 files / 48.51 MB |
| Top-level component domains | 1,509 |
| Core `frontend/` + `lovelace/` Python | 10 files / 106.9 KB |
| Python tests under `tests/` | 8,269 files / 67.45 MB |

The striking number is not the frontend wrapper size; it is that roughly **94% of the Python bytes under `homeassistant/` are component code**. Home Assistant's breadth is its strength, but ha-lite does not need every product component and every integration in order to preserve a powerful device runtime.

For that reason, the final reduction percentage is intentionally **not predicted yet**. Saying “half of Home Assistant” before the deletion waves finish would mix several different baselines and would be easy to misrepresent. Instead, every major wave should update the measured baseline so the README can eventually say exactly how much production code, tests, components and dependencies were removed.

The repository includes `script/ha_lite_size_report.py` to produce reproducible file/line/byte counts from a checkout. The same measurement can be run before and after deletion waves rather than relying on estimates.

## What success looks like

ha-lite should remain able to discover, configure, observe and control retained devices while being substantially smaller and conceptually narrower than Home Assistant Core. In particular, headless operation is a contract rather than a launch option: frontend/Lovelace must be physically absent, while HTTP/WebSocket APIs, representative integrations and MCP continue to work.

See [the architecture overview](docs/architecture/overview.md), [scope matrix](docs/architecture/scope-matrix.md), [testing strategy](docs/architecture/testing-strategy.md), and [ADRs](docs/adr/).
