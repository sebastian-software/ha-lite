# Deletion Wave 1 — frontend and dashboard product surface

## Goal

Make Home Assistant Core boot without the browser product surface while preserving device/integration runtime capabilities.

Target upstream baseline: **Home Assistant Core 2026.9.3**.

This wave is deliberately narrow. It should not yet remove automation, recorder, auth, config entries, generic entity platforms, integration-specific runtime machinery, or the Conversation/MCP substrate now classified as core.

## Why this wave comes first

The current bootstrap treats the frontend as product-critical:

- `frontend` is explicitly staged during startup;
- `frontend` is in `DEFAULT_INTEGRATIONS`;
- `frontend` is the only member of `CRITICAL_INTEGRATIONS`;
- recovery-mode defaults include `frontend`;
- `bootstrap.py` pre-imports a broad set of frontend dependencies;
- storage preload contains Lovelace keys;
- `config` imports `frontend` directly and always registers the configuration panel.

This means "do not configure frontend" is not equivalent to a headless runtime. The bootstrap contract itself must change.

## High-confidence deletes

Current Wave 1 progress: the `frontend` component has now been physically removed after its bootstrap/recovery/config coupling was eliminated. `lovelace` remains for the next deletion block so dependency failures stay attributable.

After the patches below are in place:

```text
homeassistant/components/frontend/  # REMOVED
homeassistant/components/lovelace/  # NEXT
```

Likely deletions in the same or immediately following commit, after import checks:

```text
homeassistant/components/map_tiles/
homeassistant/components/my/
```

Do not delete `config`, `http`, `auth`, `websocket_api`, `repairs`, or `diagnostics` in this wave.

## Required bootstrap patch

### 1. Remove frontend pre-import assumptions

In `homeassistant/bootstrap.py`, remove frontend-product preimports that are present only to accelerate frontend startup.

At minimum investigate/remove these preimports as part of this wave:

```text
frontend
lovelace
default_config
file_upload
image_upload
history
logbook
onboarding
person
search
```

Do **not** mechanically remove every item in the current pre-import block. Some entries such as `api`, `auth`, `config`, `diagnostics`, `http`, `repairs`, `system_log`, `webhook`, and `websocket_api` remain useful to the headless runtime.

### 2. Remove the frontend startup stage

Delete `FRONTEND_INTEGRATIONS` and the frontend substage from `STAGE_0_INTEGRATIONS`.

The intended early stages should contain operational/runtime dependencies only.

### 3. Remove frontend from defaults

Remove `frontend` from `DEFAULT_INTEGRATIONS`.

This is also an opportunity to stop using the full Home Assistant default bundle as the conceptual source of ha-lite defaults. A later wave should replace this set with an explicit minimal runtime set.

### 4. Redefine recovery mode

Remove `frontend` and `cloud` from the recovery-mode default set.

A headless recovery mode should prioritize:

- logging;
- network/http if needed for administrative API access;
- auth;
- config/config-entries repair access;
- diagnostics/repairs;
- persistence required to inspect and fix configuration.

Exact recovery composition is still INVESTIGATE; the key decision is that recovery must not mean "boot the UI".

### 5. Remove frontend criticality

Remove `frontend` from `CRITICAL_INTEGRATIONS`.

Eventually the constant itself may disappear or contain genuinely runtime-critical services.

### 6. Remove Lovelace storage preload

Delete Lovelace-specific keys from `PRELOAD_STORAGE`:

```text
lovelace_dashboards
lovelace_resources
lovelace.map
```

Also investigate `image`, `assist_pipeline.pipelines`, analytics, and backup in later waves rather than deleting them accidentally here.

### 7. Remove "open browser" behavior

`open_hass_ui()` and the `runtime_config.open_ui` path are browser-product behavior and can be removed from ha-lite.

A CLI can instead print the listening address/API status when requested.

## Required config-component patch

Current `homeassistant/components/config/__init__.py` imports `frontend` and unconditionally calls:

```python
frontend.async_register_built_in_panel(...)
```

That coupling must be removed.

The backend configuration sections should remain available independently of panel registration.

### First reduction of config sections

Current sections include backend endpoints for:

```text
area_registry
auth
auth_provider_homeassistant
automation
category_registry
config_entries
core
device_registry
entity_registry
floor_registry
label_registry
script
scene
```

For wave 1, remove only frontend registration. Automation/script/scene sections can remain temporarily to avoid combining architectural cuts.

Wave 2 will remove those sections together with the automation product.

## Dependency consequence of deleting frontend

The frontend manifest currently forces this product bundle:

```text
api
auth
config
device_automation
diagnostics
file_upload
http
lovelace
map_tiles
onboarding
repairs
search
system_log
websocket_api
```

Deleting frontend therefore stops these from being retained merely because the frontend depends on them.

Each must then earn its place independently.

Initial reassessment:

| Component | Wave-1 status |
|---|---|
| api | KEEP/INVESTIGATE |
| auth | KEEP |
| config | KEEP/REDUCE |
| device_automation | DELETE in wave 2 |
| diagnostics | KEEP/REDUCE |
| file_upload | PATCH AWAY where needed |
| http | KEEP |
| lovelace | DELETE |
| map_tiles | DELETE likely |
| onboarding | REPLACE |
| repairs | KEEP/REDUCE |
| search | INVESTIGATE; likely product/UI |
| system_log | KEEP |
| websocket_api | KEEP initially |

## Acceptance criteria

A wave-1 branch is successful when:

1. Core starts with no `frontend` package present.
2. Core starts with no `lovelace` package present.
3. Failure to load frontend cannot trigger recovery mode because frontend no longer exists as a startup concept.
4. Config entries initialize.
5. Device and entity registries load.
6. HTTP/auth/WebSocket API can start headlessly.
7. A config flow can be created and advanced through API-level primitives.
8. Shelly can at least import/setup far enough to expose remaining missing runtime dependencies.
9. Tests contain no expectation that a frontend panel exists.
10. No Lovelace storage keys are preloaded.
11. The official `mcp_server` suite remains green, including real MCP initialization, tool listing, and tool invocation without requiring frontend/Lovelace.

## Expected first breakages

Likely direct failures after deletion:

- imports of `homeassistant.components.frontend` outside the frontend package;
- code calling panel registration helpers;
- tests asserting panels/routes;
- config and onboarding cross-coupling;
- integrations with frontend-only panel setup.

These should be classified case-by-case as DELETE (product feature), PATCH (mixed concern), or KEEP (actual runtime contract).

## Commit strategy

Prefer thematic commits:

1. `bootstrap: stop treating frontend as critical`
2. `config: decouple backend config API from frontend panel`
3. `core: remove browser-open behavior`
4. `frontend: delete frontend and lovelace components`
5. `tests: remove/update frontend startup assumptions`

Keeping these separate makes future upstream archaeology easier than one giant delete commit.

## MCP guardrail added during Wave 1

Before physically deleting frontend/Lovelace, ha-lite promotes the official Home Assistant Model Context Protocol server to a retained core capability. This deliberately changes the earlier assumption that all Assist/Conversation machinery belongs to a later deletion wave.

Retain and protect the minimal dependency chain needed by `mcp_server` (`http`, `conversation`, `intent`, LLM helpers and their actual runtime dependencies). Do not retain frontend/Lovelace merely to support MCP.

The third-party `homeassistant-ai/ha-mcp` project is a compatibility target, not copied into this repository. Its hard HA dependency is `webhook`; frontend and Lovelace are optional/after-dependencies. Its embedded-server default sidebar panel is presentation-only and must be disabled for a truly headless deployment. Future compatibility testing should exercise the server/webhook/state/service paths with that panel disabled and should not require its dashboard-specific tools to work after Lovelace is removed.

### Frontend physical deletion checkpoint

The frontend deletion also removes the `home-assistant-frontend` requirement from the all-requirements/constraint sets. This repository never contained the separate upstream browser application's TypeScript source; the removed Core component was the Python integration/glue that loaded and served that packaged frontend.

The retained `tests/components/mcp_server` protocol suite now runs with the frontend package physically absent from the source tree. Its authenticated initialization, tool listing and tool invocation tests are therefore the Wave-1 headless MCP compatibility check at this checkpoint.
