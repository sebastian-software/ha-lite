# ADR 0011: Treat runtime-resolved platforms as capabilities, not dependencies

- Status: Accepted

## Context

Home Assistant resolves some platforms **by name** rather than by import.
`helpers/trigger.py` calls `async_process_integration_platforms` for `trigger`,
`helpers/condition.py` does the same for `condition`, and the runtime then
dispatches to whatever each set-up integration happens to provide. The same
pattern carries `backup`, `intent`, `reproduce_state` and `significant_change`.

No import edge exists for these, so the closure of ADR 0010 is blind to them.
Deleting a provider removes a capability **without breaking a single import**.

Wave 3 found this the expensive way. Removing Template also removed
`template/trigger.py`, and with it `platform: template` for
`websocket_api.subscribe_trigger`. Nothing failed at import time; it was noticed
only because one test happened to use it.

The naive correction — counting these as hard edges — is wrong. Providing a
platform genuinely is not a dependency: the runtime requires no particular
provider and works with none at all. Counting them would drag every domain
shipping a `trigger.py` into the retained set and make the closure useless.

## Decision

Providing a runtime-resolved platform does not grow the closure.

Instead, `script/ha_lite_closure.py` reports providers that sit **outside** the
closure as **capability at risk**, with the platforms they provide and their
`integration_type`. Deletion waves must work that list alongside the closure: a
domain that is reachable from no root and provides no cross-cutting platform is
free to delete; one that provides a platform is a deliberate capability
decision.

The watched platforms are listed in `cross_cutting_platforms` in
`script/ha_lite_closure_config.json`, so the set is reviewable rather than
hardcoded.

Self-scoped platforms are deliberately excluded. `config_flow`, `diagnostics`,
`application_credentials` and `config` only extend their own integration, so they
leave with it; warning about them would add 939 config-flow entries of noise.

## Consequences

The closure answers "what breaks if this is deleted?" and the capability report
answers "what stops being possible?". Both are required before a bulk deletion,
and neither substitutes for the other.

A reported capability is not automatically worth keeping. Most entries group
sensibly by `integration_type`: `hub` and `device` providers leave legitimately
with their integration, and `service` is largely backup storage backends. The
report exists to force the question, not to answer it.

The report immediately surfaced a finding larger than the Template case, which
ADR 0012 decides.

Wave 4 worked the list before deleting. It named 29 providers; one became a
root, and the other 28 went, each for a stated reason — backup storage agents
because backup semantics belong to the persistence contract, the `calendar`,
`geo_location`, `remote` and `todo` vocabularies because no retained
integration implements those domains, hub and device triggers with their
integration. `retained-closure.md` records the table.

ADR 0020 brought the catalog back, and with it most of those providers:
`calendar`, `geo_location`, `remote` and `todo` as entity-domain roots, the
hub and device triggers with their integrations. The list now names the
catalog members that provide a cross-cutting platform, which is what to
consult before removing one of them.

Because the mechanism is invisible to static analysis, a provider only
contributes its platform once its integration has actually been set up.
A component that ships `trigger.py` but is never set up contributes nothing.
