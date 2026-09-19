# ADR 0002: Keep automation and decision making outside the core

- Status: Accepted
- Date: 2026-09-18

## Context

Home Assistant contains automation, scripts, scenes, blueprints, schedules and helper entities used to encode decisions inside the server.

The intended ha-lite architecture separates observation/control of the physical world from decisions about desired behavior. Those decisions may be made by AI agents, deterministic applications, cron/schedulers, humans, or other external systems.

## Decision

ha-lite will not contain a general automation engine.

Automation, script and blueprint are deletion candidates. Schedule/timer and automation-oriented helper integrations are deletion candidates unless a retained device integration demonstrates a non-automation requirement.

The core **will** retain event delivery and state transitions. These are observations and runtime primitives, not automation.

Scenes are initially INVESTIGATE/DELETE: if a generic batch-command primitive is useful, it should be designed explicitly rather than inherited accidentally as automation semantics.

## Consequences

The API must make external decision engines first-class: subscribe to state/events, query current state/capabilities and issue commands.

No AI framework belongs in the device core merely because AI may be a major consumer of it. The core remains deterministic infrastructure.
