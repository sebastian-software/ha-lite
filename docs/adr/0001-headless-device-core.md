# ADR 0001: Define ha-lite as a headless device core

- Status: Accepted

## Context

Home Assistant Core carries responsibilities for a complete home-automation product. ha-lite needs a smaller architectural center. Its primary value is the mature knowledge embodied in Home Assistant's integrations and device lifecycle, not its end-user product surface.

## Decision

ha-lite is a headless physical-world runtime.

It owns device/service discovery, configuration lifecycle, identity, capabilities, observed state, actions, events, integration lifecycle, minimum persistence, authentication and a machine-oriented API.

It does not own dashboards or other browser UI. Code whose only purpose is presentation should be removed rather than merely hidden when dependencies allow it.

"Device core" bounds what ha-lite is *for*, not what its state may be about. A derived answer assembled from retained substrate stays in the core even when it is about a person rather than a device; ADR 0002 works that out for `person` and `zone`. The test is whether the answer describes the physical world, not whether its subject is a piece of hardware.

## Consequences

Home Assistant assumptions that frontend is start-critical must be removed. Backend configuration functionality currently coupled to panel/frontend registration must be separated.

A missing UI must never prevent normal startup, configuration, diagnostics, reauthentication or repair workflows. Those workflows need API/CLI representations.
