# ADR 0016: Initialize, recover and administer ha-lite without a browser

- Status: Accepted

## Context

ADR 0007 made bootstrap headless: no frontend stage, no critical integration,
no browser launch. It left three things open, and #22 and #30 closed them.

**First run.** Home Assistant creates its first user in `onboarding`, a set of
browser views. ha-lite never set onboarding up, so a fresh installation had no
supported way to create a user: `hass --script auth add` only writes login
credentials, and the user they belong to appears only after someone logs in
through the OAuth-style login flow. There was no owner at all.

**Defaults.** What a fresh installation runs came from `default_config`, a
product bundle written into the generated `configuration.yaml`, plus
bootstrap's `DEFAULT_INTEGRATIONS`, which still carried `analytics` ("needed for
onboarding"), `backup`, `brands`, `hardware` and `labs`. Nothing in the tree
said which of these ha-lite actually wanted.

**Recovery.** Recovery mode had its product entries removed and nothing put in
their place. It reached HTTP only because `backup`, its one default, happened to
depend on it. And the reason recovery started was logged by the instance that
failed, whose log file the recovery instance rotates away, so an API client
could not find out what went wrong.

## Decision

**First run is a command, not a UI.** `hass --script owner -c CONFIG create`
creates the owner — the first administrator, with username/password
credentials — and refuses once any user exists. `hass --script owner -c CONFIG
token --client-name NAME` issues a long-lived access token for the owner and
prints it once. Machine clients, MCP agents among them, authenticate with such
a token. Both commands write the auth store directly, so they run while ha-lite
is stopped; filesystem access to the configuration directory is the root of
trust, as it already is for `secrets.yaml`.

`onboarding` is removed. The checks retained code made against it behaved as
"already onboarded" whenever onboarding was not set up, which was always, so
removing them changes nothing at runtime: discovered single-instance
integrations and Bluetooth adapters wait for a client to confirm their config
flow, and `/auth/providers` answers regardless. Catalog integrations ask the
same question in their config flows; `onboarding.py`, a compat module, gives
them the same answer (ADR 0020).

**Defaults are explicit and minimal.** `DEFAULT_INTEGRATIONS` is the runtime
that is always on: the HTTP, REST and WebSocket APIs, auth, config, repairs,
diagnostics and logging, application credentials, webhooks, the entity-domain
substrate and the device-class vocabulary, and `person`, `scene`, `tag` and
`zone`. What is useful but optional is listed in the generated
`configuration.yaml` instead of hidden in a bundle: the discovery integrations
(`bluetooth`, `dhcp`, `ssdp`, `usb`, `zeroconf`), each one line to delete. A
host without Bluetooth, or a container that must not scan the network, removes
the line. `sun` is retained but added through its config flow.

`default_config`, `analytics`, `labs`, `brands`, `hardware`, `file_upload`,
`my`, `map_tiles` and `search` are removed. `backup` is no longer a default or
a recovery-mode member; ADR 0018 makes backup a copy of the configuration
directory.

An existing configuration that still says `default_config:` gets an
"integration not found" error for that key and nothing else. Replacing it with
the discovery lines above restores what it provided that ha-lite keeps.

**Recovery is an API path.** Recovery mode sets up exactly what a client needs
to authenticate and repair: `http`, `auth`, `api`, `websocket_api`, `config`,
`repairs`, `diagnostics`, `system_log` and `logger`. The recovery instance logs
the reason it started once its `system_log` is up, so it is available over
`/api/error_log` and `system_log/list`. Config entries can be listed, and
repaired once the configuration is fixed, through the same config API as
always.

**Administration is the API ha-lite already has.** No admin surface is added.
A token for an administrator reaches everything Home Assistant exposes for
administration: `config/config_entries` for flows, options, reconfigure,
reload, disable and removal; `repairs` for issues and fix flows; `diagnostics`
for config-entry and device dumps; `system_log` and `logger` for errors and log
levels; `config/auth` and `config/auth_provider/homeassistant` for users and
credentials; `auth/long_lived_access_token` and `auth/delete_refresh_token` for
tokens. Services and admin-only commands keep their admin requirement.

**Supervisor is not a runtime mode.** Bootstrap no longer adds `hassio` when
the `SUPERVISOR` variable is set, and `hassio` is not a stage-1 integration.
The component was deleted in Wave 4 (#27) and is an excluded product layer
(ADR 0020).

## Consequences

A fresh installation needs two commands before a client can connect: `create`
and `token`. That is the whole first-run story, and `tests/scripts/test_owner.py`
runs both against a configuration that never started — a plain stop of an
instance that never started skips the final write, which silently lost the owner
the first time this was tried.

`tests/ha_lite/test_headless_bootstrap.py` breaks a configuration and asserts
that recovery mode serves the API and reports why. `recovery_mode` is a root of
the closure with its own tests in CI: bootstrap sets it up by name, which the
import graph cannot see, and nothing else would have kept Wave 4 from deleting
it.

Bootstrap sets up every `Platform` member by default except `calendar` and
`todo`, as upstream does. The enum is generated from the entity domains in the
tree; Wave 4 deleted `calendar`, `geo_location`, `image_processing`,
`radio_frequency`, `remote` and `todo`, and ADR 0020 brought them back as
entity-domain roots. `tests/ha_lite/test_bootstrap_domains.py` checks that
every domain bootstrap sets up on every start, and every domain the generated
`configuration.yaml` names, is in the closure, and that the domains its stages
set up only when configured, such as `debugpy` and `sentry`, are in the tree.
