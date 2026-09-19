# ADR 0005: Distinguish runtime scheduling from user automation

- Status: Accepted
- Date: 2026-09-19

## Context

ha-lite excludes Home Assistant's automation and scheduling product features. Source analysis of retained integrations shows that asynchronous timers and periodic callbacks are nevertheless required for device operation.

For example, Fronius uses a periodic callback to rescan devices/inverters. Similar mechanisms are expected for polling, retry, backoff, refresh, expiry and housekeeping.

## Decision

Remove user-facing automation scheduling semantics, including schedule/timer helpers where they exist to model user behavior.

Retain low-level runtime scheduling primitives used internally by integrations and the core.

The distinction is responsibility:

- "turn the light on at 18:00" is external decision logic;
- "poll this inverter again in 30 seconds" is integration lifecycle.

## Consequences

Low-level event/timer helpers cannot be deleted merely because they contain scheduling functions.

Dependency analysis must distinguish imports of `homeassistant.helpers.event` and related runtime utilities from the `schedule` and `timer` product integrations.
