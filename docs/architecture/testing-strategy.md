# Testing strategy

## Principle

The Home Assistant test suite is part of the source material we are inheriting.

Reduction must not mean deleting failing tests until CI turns green. Tests should be classified by the same architectural boundary as production code.

A test may be removed only when the behavior it protects has been explicitly classified as out of scope. Tests for retained runtime contracts must stay green, even if their implementation is refactored substantially.

## Baseline first

Before Deletion Wave 1 touches Home Assistant production code, `.github/workflows/ha-lite-ci.yml` establishes a green baseline against the imported Home Assistant Core 2026.9.3 source.

The baseline is intentionally narrower than Home Assistant upstream CI but broader than the five representative integrations. It protects the contracts that those integrations rely on.

## Required suites

### Core runtime

These tests protect lifecycle and integration-host behavior:

- `tests/test_bootstrap.py`
- `tests/test_core.py`
- `tests/test_config.py`
- `tests/test_config_entries.py`
- `tests/test_loader.py`
- `tests/test_setup.py`
- `tests/helpers/test_condition.py`
- `tests/helpers/test_device_registry.py`
- `tests/helpers/test_entity_registry.py`
- `tests/helpers/test_storage.py`

A headless/reduced core is not acceptable if these contracts silently regress.

### Headless infrastructure

Protected as directories:

- `tests/components/api`
- `tests/components/auth`
- `tests/components/http`
- `tests/components/websocket_api`
- `tests/components/config`
- `tests/components/logger`
- `tests/components/system_log`
- `tests/components/system_health`
- `tests/components/application_credentials`
- `tests/components/webhook`
- `tests/components/persistent_notification`
- the `homeassistant` integration's init, exposed-entities and repairs tests
- `tests/components/network`
- `tests/components/zeroconf`
- `tests/components/bluetooth`
- `tests/components/dhcp`
- `tests/components/ssdp`
- `tests/components/usb`
- `tests/components/repairs`
- `tests/components/diagnostics`
- `tests/components/conversation`
- `tests/components/mcp_server`
- `tests/components/media_source`
- `tests/components/recovery_mode`
- `tests/ha_lite`, contracts ha-lite adds on top of the upstream suite: the headless MCP round-trip and headless recovery mode

Tests inside these directories may later be split into retained runtime behavior versus Home Assistant product/UI behavior. Until that split is explicit, they remain a safety net.

### Entity domains, device-class semantics and derived state

Every other root of the closure has its own matrix job: the entity-domain
substrate, the fifteen device-class trigger and condition providers, and
`group`, `person` and `sun`. [retained-closure.md](retained-closure.md) lists
them; ADR 0020 is why a root without a job is not allowed.

### Representative integrations

The complete test directories for these integrations are required:

- Shelly
- MQTT
- Matter
- Hue
- Fronius
- Modbus
- Miele, the OAuth lifecycle anchor (ADR 0017)

The whole integration directory is tested rather than a hand-picked test subset. This protects config flows, migrations, entity behavior, diagnostics, lifecycle, discovery, failures and edge cases already learned by Home Assistant.

### Catalog

Every other integration in the tree is a catalog member (ADR 0020), and the `catalog` job runs its full test directory as upstream ships it. The job is split into ten shards; `script/ha_lite_catalog_shard.py` weighs each directory by the size of its test modules and hands them out so the shards take similar time. Device-trigger tests keep working without the Automation product because `tests/components/__init__.py` routes `automation` and `script` setups to the retained trigger, condition and action primitives in `tests/helpers/automation_harness.py`.

## Classification of test failures during reduction

Every failure caused by a deletion must be assigned one of four outcomes:

1. **Regression — fix production code.** The test protects retained behavior.
2. **Interface migration — adapt the test.** The behavior remains, but its presentation/API changed (for example panel UI to headless API).
3. **Product behavior removed — delete or replace the test.** The behavior is explicitly outside ha-lite scope and the associated production code is deleted.
4. **Hidden dependency discovered — update architecture classification.** The test reveals a dependency we did not understand. Do not patch around it blindly.

The reason for outcomes 2–4 should be captured in the relevant ADR/deletion-wave document or commit message.

## CI shape

The workflow started with four gates and has since grown a matrix per root category:

```text
prepare environment
       |
       +--> core runtime
       +--> headless infrastructure
       +--> entity-domain substrate (matrix)
       +--> device-class semantics (matrix)
       +--> derived state (matrix)
       +--> retained integrations (matrix)
       +--> catalog (10 shards)
       +--> test fixtures (demo, kitchen_sink)
       +--> static sanity (prek, the gates' own tests, trigger targets, closure gate,
                           hassfest, requirement files, mypy)
```

The dependency environment is built once and cached. Matrix suites run separately so a failure in Matter does not obscure a Shelly regression.

## Full upstream suite

Running all ~Home Assistant tests on every ha-lite change is not a useful long-term goal because thousands of tests protect integrations and product features we intend to remove.

Wave 4 answered that question by deleting the integrations, and ADR 0020 reversed the deletion. With the catalog back, every root has a CI job running its tests and the `catalog` job runs every other integration's suite, so CI covers every integration in the tree. What does not run yet is most of `tests/helpers` and `tests/util`, and the own suites of the transitive members (`device_automation`, `intent`, `llm`, `manual`, `stream`, `web_rtc`, `zone`). Adding them is ordinary coverage work, not a separate full-suite run.

## Adding integrations

An integration copied in from upstream joins the catalog: the closure gate accepts it once nothing it imports is missing, and the `catalog` job runs its suite.

When an integration is promoted to an anchor, a root CI runs on its own:

1. add its full `tests/components/<domain>` directory to the CI matrix;
2. add its manifest/import dependencies to the dependency map;
3. classify any new generic runtime dependencies;
4. keep its config-flow/migration tests unless the corresponding lifecycle is intentionally replaced.

## Removing tests

Deletion of a test should be reviewable as an architectural decision.

For large component removals, deleting the component and its tests together is expected. For mixed components, prefer retaining or rewriting tests around the reduced responsibility instead of bulk deletion.

## Agent/MCP runtime contract

The official Home Assistant MCP server is a retained ha-lite capability, not optional test coverage. CI runs the upstream `tests/components/mcp_server` suite because it already exercises the real protocol surface, including authenticated initialization over SSE/streamable HTTP, tool enumeration and service-affecting tool invocation.

`conversation` is tested alongside it because it is a hard dependency of `mcp_server`. Passing import-only tests is insufficient: protocol-level MCP tests are the contract.

`tests/ha_lite/test_mcp_headless.py` is the ha-lite-specific assertion Wave 1 called for. It checks that the removed browser, voice and AI products cannot be imported, runs initialize, tool listing and a device-affecting tool call over streamable HTTP, and fails if that session loads any component outside the retained closure — so a future upstream change that makes MCP lean on something ha-lite deleted, or on something it never reviewed, fails here rather than in production.

`homeassistant-ai/ha-mcp` is an external compatibility canary. A later CI layer may install its current custom component and exercise its embedded server with `enable_sidebar_panel=false`; avoid vendoring its implementation or requiring dashboard/Lovelace tools as part of the ha-lite core contract.
