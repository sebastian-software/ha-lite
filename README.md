# ha-lite

A headless, deliberately reduced device runtime exploring how much of Home Assistant's integration knowledge can be retained without carrying the complete Home Assistant product.

> Early architecture and reduction experiment. Not yet a usable Home Assistant distribution.

## Direction

ha-lite treats Home Assistant Core as high-value source material rather than an architectural constraint. The target runtime is responsible for the physical-world boundary:

- discover and configure devices and services;
- maintain stable device and entity identities;
- observe and normalize state;
- expose capabilities and actions;
- publish events and state changes;
- persist the minimum state and configuration required for reliable operation;
- provide a small machine-oriented API.

Decision making belongs outside the core. Automations, schedules, dashboards, scenes, assistants, and other product-level features are not intended to be part of the runtime.

See `docs/architecture/overview.md`, `docs/architecture/scope-matrix.md`, and `docs/adr/`.
