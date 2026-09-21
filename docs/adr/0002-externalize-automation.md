# ADR 0002: Keep automation and decision making outside the core

- Status: Accepted

## Context

Home Assistant contains automation, scripts, scenes, blueprints, schedules and helper entities used to encode decisions inside the server.

The intended ha-lite architecture separates observation/control of the physical world from decisions about desired behavior. Those decisions may be made by AI agents, deterministic applications, cron/schedulers, humans, or other external systems.

## Decision

ha-lite will not contain a general automation engine.

Automation, script and blueprint leave the core. Schedule/timer and automation-oriented helper integrations leave too, unless a retained device integration demonstrates a non-automation requirement.

`automation`, `script`, `blueprint`, `schedule`, `timer`, `counter` and the six `input_*` helpers have since been removed. None of them survived the non-automation test: each was held in only by a `_domain_specs` entry in some retained domain's trigger or condition platform, and dropping that entry was enough to make it fall out of the closure.

The core **will** retain event delivery and state transitions. These are observations and runtime primitives, not automation.

The vocabulary an external engine uses to *describe* what it wants to observe is also not automation, and stays. ADR 0012 draws that line for the device-class trigger and condition providers.

`scene` is still reached from `config/scene.py` and has not been resolved. If a generic batch-command primitive is useful it should be designed explicitly, rather than inherited accidentally as automation semantics.

## Consequences

The API must make external decision engines first-class: subscribe to state/events, query current state/capabilities and issue commands.

No AI framework belongs in the device core merely because AI may be a major consumer of it. The core remains deterministic infrastructure.
