# ADR 0006: Preserve Home Assistant integration contracts before replacing them

- Status: Accepted

## Context

Representative integrations depend on substantially more than their protocol libraries. They use config entries, registries, entity-domain classes, coordinators, HTTP helpers, discovery and lifecycle facilities.

At the same time, some integrations contain direct coupling to Home Assistant product features. MQTT's configuration flow couples certificate setup to file-upload/UI machinery and Hass.io conveniences. Matter couples configuration/runtime paths to Hass.io add-on management and onboarding.

## Decision

During the reduction phase, preserve the generic Home Assistant runtime contracts required by retained integrations.

Patch product-specific coupling out of retained integrations instead of retaining whole product subsystems solely to satisfy those imports.

Classify every dependency as either:

1. integration/runtime contract to preserve;
2. protocol/library dependency;
3. product convenience to remove;
4. presentation/config UX to replace.

## Consequences

A manifest's transitive dependency closure is a starting point, not the final ha-lite architecture.

Entity-domain components such as sensor, switch, light and climate are considered runtime substrate when retained integrations import their entity contracts.

The project should prefer small portability patches in integrations over keeping Supervisor, onboarding, frontend or other product layers.
