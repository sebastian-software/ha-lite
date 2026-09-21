# ADR 0007: Make bootstrap headless rather than merely disabling frontend

- Status: Accepted

## Context

In Home Assistant Core 2026.9.3, frontend is woven into startup semantics. It has a dedicated startup stage, is loaded by default, is considered critical for successful startup, is part of recovery mode, and causes a broad product dependency bundle to be preloaded.

The backend `config` component also imports frontend directly in order to register a configuration panel.

Therefore a configuration option that simply avoids loading frontend would leave product assumptions inside the core.

## Decision

ha-lite bootstrap will have no frontend concept.

Remove frontend from startup staging, default integrations, critical-integration checks, recovery semantics and storage preload.

Remove browser-launch behavior from the runtime.

Decouple backend configuration APIs from frontend panel registration.

## Consequences

Frontend and Lovelace can be physically deleted without making startup invalid.

Recovery mode must be redefined as an operational/API recovery path. **Still open.** `DEFAULT_INTEGRATIONS_RECOVERY_MODE` in `homeassistant/bootstrap.py` is still Home Assistant's recovery mode with the product entries removed, not a headless recovery path of its own.

Components previously retained only because frontend depended on them must be individually reclassified.

This intentionally increases divergence from upstream bootstrap code, but produces a much clearer architectural boundary.
