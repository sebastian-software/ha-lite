# ADR 0019: Keep YAML as input, ship the tree's dependencies, gate both in CI

- Status: Accepted

## Context

#29 asked whether the configuration stack and dependency installation still
fit ha-lite after Wave 4: which YAML the runtime needs, whether YAML should
stay, and whether installing requirements at runtime should give way to a
pre-resolved dependency set. Upstream answers all three for the full
Home Assistant catalog. With the tree reduced to the closure, they can be
answered for what ha-lite actually runs.

**YAML the retained runtime reads.** Two kinds, and both are real:

- *Instance configuration* that has to exist before any config entry loads:
  the `homeassistant:` section (location, units, packages, customization),
  `http:` (ports, TLS, proxies, IP bans), `logger:`, and the discovery lines
  in the generated `configuration.yaml` (ADR 0016).
- *Declarative integration configuration* with no config flow to replace it:
  Modbus's hubs and register maps (Modbus has no config flow at all), MQTT
  entities defined in YAML next to the config-entry broker, `group`, `person`,
  `zone` and `scene` definitions, custom conversation sentences, Shelly's CoAP
  port, and the `stream`, `system_log` and `web_rtc` settings.

Packages, `!include` and `!secret` are how that configuration is organized,
and `check_config` and recovery mode read it through the same code.

**Dependencies.** `requirements_all.txt` is generated from the manifests in
the tree. Over the full catalog it listed 1,146 packages; over the closure it
listed 40, on top of the 50 core requirements in `requirements.txt`. The loader
installs a missing requirement at runtime unless `--skip-pip` is given, and
that is the only way custom integrations get theirs.

**Enforcement.** CI skipped hassfest, the requirements generator and mypy in
its static job, because none of them passed over the full catalog. After
Wave 4 all three pass, and they still do over the restored catalog
(ADR 0020).

## Decision

**YAML stays as input, config entries stay primary.** Everything in the
inventory above serves a retained integration or the instance itself, so
nothing in the configuration stack is removed. The catalog reads it the way
upstream does. New integrations are expected to configure through config
flows, as upstream requires. YAML is for instance settings and for declarative device
definitions such as Modbus register maps.

**The tree's dependencies are the distribution.** This decision first read
"the closure's dependencies", which made `requirements_all.txt` 40 packages.
ADR 0020 brought the catalog back, and the file now lists 1,085. A deployment
chooses between two installs:

- `requirements.txt` and `requirements_all.txt`, as CI and upstream's
  container image do. Every integration then finds its requirements present,
  so ha-lite installs nothing at runtime and starts offline.
- `requirements.txt` alone. The loader installs an integration's
  requirements when it is first set up, as upstream Home Assistant does.

Runtime installation stays, for the catalog and for custom integrations,
whose contract ADR 0006 preserves. A deployment that must not install
anything runs with `--skip-pip` and pre-installs what it needs.

**The generators are enforced, not rewritten.** The "full catalog" assumption
was never in the code of `gen_requirements_all` or hassfest. It was in their
input, and their input is the tree: the closure and the catalog. They stay upstream code
(ADR 0014). The static CI job now runs, over the whole tree:

- `python -m script.hassfest --action validate`: manifests, generated
  matchers, config-flow and platform lists, mypy configuration and the rest
  of hassfest's checks match the tree;
- `python -m script.gen_requirements_all validate`: `requirements.txt`,
  `requirements_all.txt` and `homeassistant/package_constraints.txt` match
  the manifests;
- `mypy homeassistant pylint`: the runtime type-checks.

`tests/test_config.py` joins the core CI job. Its package-merge tests used
to set up `input_boolean`, `automation` and other deleted integrations, and
some passed only because "integration not found" counted as the merge error
they expected. They now use retained integrations of each merge shape:
`group`, `logger` and `system_log` merge as dictionaries, `person`, `zone` and
`modbus` as lists.

## Consequences

Adding an integration means regenerating the requirement files with it;
leaving that out fails CI. A root also needs its CI job (ADR 0020).

A deployment that installs `requirements_all.txt` needs no package index at
runtime. One that adds custom integrations behaves like upstream Home
Assistant.

The configuration code keeps upstream's generality: packages can still name
any domain, and a package that names a missing integration logs an error, as
it always did. Narrowing the YAML surface further would mean patching
upstream configuration code for no retained behavior, so it waits for a
concrete reason.
