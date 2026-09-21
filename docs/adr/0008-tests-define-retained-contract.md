# ADR 0008: Use tests to define the retained runtime contract

- Status: Accepted

## Context

ha-lite is intentionally removing large parts of Home Assistant. A mechanically shrinking test suite would make aggressive deletion easy but would also discard years of learned edge cases, lifecycle behavior and device compatibility.

At the same time, retaining every upstream test forever would preserve the complete Home Assistant product by proxy.

## Decision

Tests follow architectural responsibility.

Tests protecting retained core/runtime behavior and retained integrations remain mandatory and green.

Tests may be removed when the production behavior they protect is explicitly removed from ha-lite scope. When behavior remains but moves from a UI/product interface to a headless interface, tests should be adapted rather than deleted.

Scope removal is the only justification. A test that is merely redundant, while the behavior it covers stays in scope, is left alone: ADR 0014 explains why efficiency does not buy the divergence.

Before the first production-code deletion, establish a CI baseline covering:

- core lifecycle, config entries, loading and setup;
- device/entity/storage registries;
- auth, HTTP, WebSocket and backend configuration;
- discovery/network infrastructure;
- repairs and diagnostics;
- the complete Shelly, MQTT, Matter, Hue, Fronius and Modbus test directories.

## Consequences

A deletion PR/commit cannot be justified merely by making tests disappear.

Test failures become useful dependency-discovery signals.

As the repository shrinks, the test suite should shrink for documented architectural reasons rather than as incidental cleanup.

The focused ha-lite CI suite, not the complete upstream Home Assistant suite, becomes the required regression contract.
