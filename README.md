# ha-lite

**Home Assistant's device layer as a small, headless server.**

ha-lite connects to your devices the way Home Assistant does: the same
integrations, the same discovery and the same device and entity model. It then
hands them to software rather than to people, over REST, WebSocket and the
Model Context Protocol (MCP). It has no user interface, no automation engine
and no history database. What should happen in your home is decided by
whatever you connect to it: an AI agent, your own service, or a rules engine
of your choice.

> **Status:** experimental. ha-lite is derived from Home Assistant Core
> 2026.9.3 and is not a drop-in replacement for it. There is no migration path
> from an existing Home Assistant installation.

## Is it for you?

**Use Home Assistant** if you want a smart-home application: dashboards, the
mobile apps, an automation editor, a voice assistant, history graphs, add-ons,
cloud access and thousands of integrations. That is what Home Assistant is
built for, and ha-lite removes all of it.

**Consider ha-lite** if you already have the brain and need the hands: a
dependable way to discover, configure, observe and control real devices, with
a small codebase you can read and a dependency list you can audit. It is
built for AI agents over MCP, custom control services, and anyone who wants
Home Assistant's device knowledge without the product around it.

## How it differs from Home Assistant

| | Home Assistant | ha-lite |
| --- | --- | --- |
| **Interface** | Web app, dashboards, mobile apps | None — REST, WebSocket and MCP |
| **Automations and scripts** | Built in, with an editor, blueprints and templates | Not included. Your client subscribes to events and calls services |
| **AI agents** | Assist and conversation agents; MCP server as an option | MCP server as a primary interface |
| **Integrations** | About 1,500 | 90: seven device integrations and what they build on |
| **History and statistics** | Recorder database, history graphs, energy dashboard | None. State changes are streamed, and clients keep what they need |
| **First run** | Onboarding wizard in the browser | Two commands create the owner and an access token |
| **Broken configuration** | Recovery mode in the browser | Recovery mode serves the API and reports the cause |
| **Cloud, add-ons, OS** | Nabu Casa, Supervisor, add-ons, Home Assistant OS | None |
| **Backup** | Backup integration with cloud storage agents | Copy the configuration directory |
| **Python source** | 51 MB in 10,000 files | 8 MB in 925 files |
| **Integration dependencies** | Over 1,100 pinned packages | 40 pinned packages |

## What stays the same

ha-lite keeps Home Assistant's runtime and integration code as it is, so an
integration behaves the way it does upstream:

- **Integrations and config flows.** Devices are added through the same
  config flows, with reauthentication, reconfiguration and options.
- **Discovery.** Zeroconf/mDNS, SSDP, DHCP, Bluetooth and USB find devices
  and start their config flows.
- **Devices and entities.** The device and entity registries, the state
  machine, the event bus and service calls are unchanged. So are areas,
  floors and labels.
- **Entity domains.** Lights, switches, covers, climate, fans, locks, sensors,
  binary sensors, media players, vacuums, valves, water heaters, cameras,
  weather and the other domains the retained integrations provide.
- **Triggers and conditions.** Named vocabulary such as `motion.detected`,
  `door.opened` or `temperature.crossed_threshold`, subscribable over the
  WebSocket API.
- **Derived state.** Scenes, groups, people and zones, and the sun's position.
- **APIs.** The REST and WebSocket APIs, webhooks, OAuth2 application
  credentials, and the MCP server.

### Included integrations

| Integration | Kind |
| --- | --- |
| [Shelly](https://www.home-assistant.io/integrations/shelly) | Local devices over HTTP/CoAP/RPC and Bluetooth |
| [MQTT](https://www.home-assistant.io/integrations/mqtt) | Any device that speaks MQTT, including MQTT discovery |
| [Matter](https://www.home-assistant.io/integrations/matter) | Matter devices through an external Matter Server |
| [Philips Hue](https://www.home-assistant.io/integrations/hue) | Hue bridges |
| [Fronius](https://www.home-assistant.io/integrations/fronius) | Fronius solar inverters |
| [Modbus](https://www.home-assistant.io/integrations/modbus) | Modbus TCP/RTU devices, configured in YAML |
| [Miele](https://www.home-assistant.io/integrations/miele) | Miele appliances through Miele's cloud (OAuth) |

Each one runs its full upstream test suite in CI. Custom integrations in the
configuration directory's `custom_components/` folder load as they do in Home
Assistant.

## What is gone, and why

Everything that makes Home Assistant a product for people is removed from the
code base, not just switched off: the frontend and dashboards, automations and
scripts, blueprints and templates, history, logbook and energy, the Recorder
database, the voice pipeline, onboarding, Home Assistant Cloud, Alexa and
Google Assistant, the Supervisor and add-ons, and backups. In all, roughly
1,400 of Home Assistant's 1,500 integrations are gone.

The principle behind the cut: ha-lite describes and controls the physical
world, and deciding what should happen belongs to its clients. Whatever is not
in the tree cannot add dependencies, coupling, attack surface or noise for the
next person or agent reading the code.

## Getting started

You need Python 3.14 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/sebastian-software/ha-lite.git
cd ha-lite
uv venv --python 3.14
source .venv/bin/activate
uv pip install -e . -r requirements_all.txt
```

`requirements_all.txt` holds every dependency of the included integrations,
so ha-lite installs nothing at runtime unless you add custom integrations.

### First run

There is no onboarding UI. Create the owner and an access token, then start
the server:

```bash
hass --script owner -c config create --name "Admin" --username admin
hass --script owner -c config token --client-name "my agent"
hass -c config
```

`create` asks for the password, and `token` prints a long-lived access token
once; keep it. The server listens on port 8123. The generated
`config/configuration.yaml` switches on device discovery, one line per
protocol. Delete a line to turn that protocol off.

### Connect an MCP client

The MCP server is set up like any integration, through its config flow:

```bash
TOKEN="<the printed token>"
API=http://localhost:8123/api

curl -s -X POST "$API/config/config_entries/flow" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"handler": "mcp_server"}'

# Use the flow_id from the response:
curl -s -X POST "$API/config/config_entries/flow/<flow_id>" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"llm_hass_api": ["assist"]}'
```

Then point your MCP client at `http://<host>:8123/api/mcp` (Streamable HTTP),
with the token as a bearer token. Devices are added the same way: start the
config flow of an integration, such as `"handler": "shelly"`, or finish one
that discovery has already started.

### When something is broken

If `configuration.yaml` cannot be loaded, ha-lite starts in recovery mode.
The API stays up, the cause is at `/api/error_log`, and config entries can be
inspected and repaired through the same API.

### Backup

Stop ha-lite and copy the configuration directory. To restore, copy it back
before starting. The directory holds credentials and secrets, so protect the
copy accordingly.

## Project documentation

The design decisions are written down as architecture decision records in
[`docs/adr/`](docs/adr/). A few starting points:

- [ADR 0001](docs/adr/0001-headless-device-core.md): why ha-lite is a
  headless device core;
- [ADR 0002](docs/adr/0002-externalize-automation.md): why decision making
  lives outside it;
- [ADR 0016](docs/adr/0016-headless-first-run-and-recovery.md): first run,
  recovery and administration without a browser;
- [ADR 0018](docs/adr/0018-persistence-contract.md): what ha-lite persists,
  and why it keeps no history;
- [ADR 0019](docs/adr/0019-configuration-and-dependencies.md): configuration
  and dependencies.

What is kept, and why, is listed per component in the
[scope matrix](docs/architecture/scope-matrix.md). The
[retained closure](docs/architecture/retained-closure.md) explains how the
kept set is computed from the import graph and enforced in CI. The
[roadmap](docs/architecture/roadmap.md) records how the reduction was carried
out, with size measurements at each step.

## Development

```bash
script/setup                        # virtual environment with dev tools
uv run --no-sync pytest tests/...   # tests
uv run --no-sync prek run --all-files
```

An integration becomes part of ha-lite by being declared in
`script/ha_lite_closure_config.json` and given a job in
`.github/workflows/ha-lite-ci.yml`. CI rejects any component that is in the
tree but not part of the declared set. [`CLAUDE.md`](CLAUDE.md) has the
project conventions.

## License

Apache License 2.0, like Home Assistant. See [LICENSE.md](LICENSE.md).
