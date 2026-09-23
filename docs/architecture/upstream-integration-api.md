# Why Home Assistant has no stable integration API

Home Assistant keeps every integration in one repository and ships them in one
package. It has never promised a stable, versioned API to code outside that
repository. ha-lite inherits both facts, and ADR 0021 has to work with them.
This document collects what the Home Assistant project has said and decided,
with links, so the reasons do not have to be rediscovered.

How the sources were read: the published sites (developers.home-assistant.io,
home-assistant.io, hacs.xyz) were read from the Markdown in their GitHub
repositories. Those were `home-assistant/developers.home-assistant` at
`17a7d24`, `home-assistant/home-assistant.io` at `586c9bc` and
`home-assistant/architecture` at `f4e5664`. The links below point to the
published pages. Issues were read on GitHub.

## The short answer

- **Integrations are part of the core code base.** "Core integrations live in
  the `homeassistant/components` directory, and do not need a `version` key.
  The architecture is the same in both cases."
  ([Creating your first integration](https://developers.home-assistant.io/docs/creating_component_index))
  When the core changes, the integrations in the repository change with it.
  Everyone else migrates on their own: "All integrations in Home Assistant have
  been upgraded. Custom component authors need to do the migration
  themselves."
  ([Entity class names, 2020](https://developers.home-assistant.io/blog/2020/05/14/entity-class-names))
- **Code outside the repository is not supported.** "The Home Assistant project
  does not review, security audit, maintain, or support third-party custom
  integrations."
  ([Architecture ADR 0022, Integration quality scale](https://github.com/home-assistant/architecture/blob/master/adr/0022-integration-quality-scale.md))
  The loader logs a warning for every custom integration. It also keeps a
  list, `BLOCKED_CUSTOM_INTEGRATIONS`, of custom integration versions it
  refuses to load
  ([`homeassistant/loader.py`](https://github.com/home-assistant/core/blob/dev/homeassistant/loader.py)).
- **The version number carries no compatibility promise.** Home Assistant uses
  calendar versioning ([Versioning](https://developers.home-assistant.io/docs/versioning)),
  and has done so since 2020.12
  ([release notes](https://www.home-assistant.io/blog/2020/12/13/release-202012/)).
  A version says when a release shipped, not what it broke.
- **What is protected is the transition, not the interface.** Since August 2026
  the [deprecation policy](https://developers.home-assistant.io/docs/deprecating)
  gives "constants, helpers, entity properties, platform APIs used by custom
  integrations" at least 12 months and an announcement on the developer blog.
  User-facing changes get 6 months. "A deprecation period may be extended if the
  ecosystem has not caught up, but it is never shortened."
- **Protocol code already lives outside, in libraries.** "One of the
  foundational rules of Home Assistant is that we do not include any protocol
  specific code. Instead, this code should be put into a standalone Python
  library and published to PyPI."
  ([Building a Python library](https://developers.home-assistant.io/docs/api_lib_index))
  What stays in the repository is the part that is coupled to the core: the
  glue between a library and Home Assistant's entities, config flows and
  helpers.

Put together: the project decided early to evolve its internals freely and to
carry every integration along in the same repository. A stable API would have
made the first harder, and the monorepo made it unnecessary for everything the
project itself maintains.

## Timeline

| When | What | Source |
|---|---|---|
| 2018-12 | Paulus Schoutsen (balloob) proposes "packaged components" that "can be independently distributed and updated. Not just by us, but by others too", adding "this is just a future vision, not to be discussed in this issue!". What shipped was one folder per integration; separate distribution did not. | [architecture#124](https://github.com/home-assistant/architecture/issues/124) |
| 2019-02 | "The Great Migration" moves every integration into its own folder: "By doing so, we can prevent custom platforms or components from breaking if a Home Assistant upgrade moves internal files/values around." | [Developer blog](https://developers.home-assistant.io/blog/2019/02/19/the-great-migration) |
| 2019-02 | HACS starts as a community project. | [HACS announcement, 2024](https://www.home-assistant.io/blog/2024/08/21/hacs-the-best-way-to-share-community-made-projects/) |
| 2019-04 | balloob proposes: "We should start releasing Home Assistant Core using semantic versioning", and "Integrations should specify in their manifest the min and max versions of Home Assistant Core they support." Closed as not planned. | [architecture#202](https://github.com/home-assistant/architecture/issues/202) |
| 2019-06 | A user asks that "Components should live in their own repository". Closed. | [core#24552](https://github.com/home-assistant/core/issues/24552) |
| 2020-04 | A proposal for an official deprecation policy, which observed that deprecations were applied inconsistently, is closed as not planned. | [architecture#368](https://github.com/home-assistant/architecture/issues/368) |
| 2020-05 | Entity base classes are renamed; all integrations in the repository are migrated with it, custom ones are on their own. | [Developer blog](https://developers.home-assistant.io/blog/2020/05/14/entity-class-names) |
| 2020-12 | Calendar versioning replaces the old version scheme. | [Release notes](https://www.home-assistant.io/blog/2020/12/13/release-202012/) |
| 2021-01 | After directory-traversal vulnerabilities in several custom integrations, HACS among them: "Custom integrations are not created and/or maintained by Home Assistant. Users install them at their own risk." | [Security disclosure](https://www.home-assistant.io/blog/2021/01/23/security-disclosure2/) |
| 2023-06 | YAML configuration options get a deprecation period of at least 6 months. | [Architecture ADR 0021](https://github.com/home-assistant/architecture/tree/master/adr) |
| 2024-08 | HACS 2.0; HACS becomes an Open Home Foundation collaboration partner, and remains "an optional addition … at the cost of stability". | [HACS announcement](https://www.home-assistant.io/blog/2024/08/21/hacs-the-best-way-to-share-community-made-projects/) |
| 2024-09 | A deprecation is extended by six months "due to the large number of custom integrations that still use them and the recent HACS v2 update". | [Developer blog](https://developers.home-assistant.io/blog/2024/09/11/extending-deprecation-hass-components) |
| 2025-04 | HACS is donated to the Open Home Foundation. | [State of the Open Home recap](https://www.home-assistant.io/blog/2025/04/16/state-of-the-open-home-recap/) |
| 2026-07 | Devices are limited to one config entry, "a breaking change without a backwards compatibility shim". | [Developer blog](https://developers.home-assistant.io/blog/2026/07/21/device-registry-single-config-entry) |
| 2026-08 | The deprecation policy is written down: 12 months for developer-facing APIs, 6 months for users. | [Deprecating](https://developers.home-assistant.io/docs/deprecating) |
| 2026-09 | Custom integrations' requirements can break the installation: "When it pins a package Home Assistant also needs, pip happily downgrades that package and takes the whole installation down with it." | [core#181913](https://github.com/home-assistant/core/pull/181913) |

## How often the interface moves

The [developer blog](https://developers.home-assistant.io/blog) is where
changes to internal APIs are announced. The release notes point custom
integration developers there
([2026.9 release notes](https://www.home-assistant.io/blog/2026/09/02/release-20269/)).

Between September 2024 and September 2026 the blog published 113 posts. 42 of
them mention a deprecation and 35 mention custom integrations. Some are about
the frontend or apps, so the numbers are upper bounds. Examples that touch
every integration:

- storing runtime data in the config entry
  ([2024-04](https://developers.home-assistant.io/blog/2024/04/30/store-runtime-data-inside-config-entry));
- removing `hass.components`;
- the options-flow change (2024-11);
- new config entry states (2025-02);
- the condition and script API (2026-05);
- one config entry per device (2026-07).

The architecture repository's own ADR 0008 on code owners
([ADR folder](https://github.com/home-assistant/architecture/tree/master/adr))
lists "Contributions refactoring across multiple integrations, caused by
changes to our core codebase" as a normal kind of change. It is the monorepo
at work.

## The line Home Assistant draws: libraries outside, glue inside

The project does split its code, just not where a plugin system would:

- "All communication to external devices or services must be wrapped in an
  external Python library hosted on pypi."
  ([Development checklist](https://developers.home-assistant.io/docs/development_checklist))
- "All API specific code has to be part of a third party library hosted on
  PyPi. Home Assistant should only interact with objects and not make direct
  calls to the API."
  ([Code review checklist](https://developers.home-assistant.io/docs/creating_component_code_review))
- The reason given: "The Home Assistant codebase would be massive if we had to
  implement the communication with the product or service in the integration
  itself … This also allows the library to be reused by other projects."
  ([Contributing to core](https://developers.home-assistant.io/docs/core/integration/contributing_to_core))
- The quality scale's Bronze tier requires the dependency to be on PyPI, and
  "There are no exceptions to this rule."
  ([dependency-transparency](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/dependency-transparency))

The libraries are versioned independently and installed on demand. The
integration code that uses them is the part coupled to the core's internals,
and that part stays in the monorepo.

A separate question, often confused with this one, is whether devices should
integrate through an external API instead of an integration. Home Assistant
decided against that "because of interoperability"
([Why Home Assistant doesn't have an external API for integrations, 2021](https://www.home-assistant.io/blog/2021/05/12/integrations-api/)).
That decision is about devices, not about plugins.

## HACS

HACS, the Home Assistant Community Store, installs custom integrations and
frontend elements from GitHub. Joakim Sørensen started it in 2019, and he
describes it as "an optional addition to Home Assistant. Giving users the
choice to add new features to Home Assistant at the cost of stability"
([2024 announcement](https://www.home-assistant.io/blog/2024/08/21/hacs-the-best-way-to-share-community-made-projects/)).
It has belonged to the Open Home Foundation since 2025, and it still carries
the project's disclaimer: "Custom elements are not supported by the Home
Assistant project. They are not reviewed or tested by the Home Assistant
development team."
([HACS documentation](https://github.com/hacs/documentation/blob/main/source/includes/abbreviations.md))

So the official answer to "plugins" is a community store for unsupported
code. Integrations that the project reviews, tests and migrates live in the
monorepo. The deprecation policy, and its extensions for HACS users, are how
the project limits the damage its internal changes do to everything else.

## Other projects

- **openHAB** keeps official add-ons in a repository separate from the core,
  but maintains them centrally: "Add-ons that got accepted in here will be
  maintained (e.g. adapted to new core APIs) by the openHAB Add-on
  maintainers." ([openhab-addons](https://github.com/openhab/openhab-addons))
  The repositories are split, and the lockstep maintenance remains.
- **Node-RED** nodes are npm packages that declare the Node-RED versions they
  support ([Packaging](https://nodered.org/docs/creating-nodes/packaging)).
- **ioBroker** adapters are separate repositories and npm packages that declare
  the `js-controller` version they need
  ([ioBroker.repositories](https://github.com/ioBroker/ioBroker.repositories)).

Node-RED and ioBroker have what Home Assistant never promised: a core API
narrow enough to version. openHAB is closer to Home Assistant's model:
separate artefacts, central maintenance.

## What this means for ha-lite

ha-lite's catalog is Home Assistant's, so it depends on the same interface:
about 1,400 names of the core, measured in
[split-distribution.md](split-distribution.md). Upstream changes that
interface every month and migrates its integrations in the same change.
ha-lite takes those changes with every upstream import (ADR 0003).

That is why ADR 0021 splits only the distribution and locks versions. What
Home Assistant guarantees internally, that every integration works with the
core it was released with, is the only guarantee ha-lite can inherit. A
stable API would be ha-lite's own promise on top of a moving upstream. The
level-2 gate in the plan measures how much each upstream import moves the
interface, which is what such a promise would cost.

## Not verified

- A maintainer's direct explanation of why integrations stay in the monorepo.
  The reasons above come from the rules, migrations and decisions themselves,
  not from a single statement.
- The reasons for closing architecture#202 and core#24552. Their comment
  threads could not be read.
- A general statement that internal APIs may change in any release. Individual
  pages say so for their own subject, e.g. "The API may change without a
  deprecation notice" ([Automations](https://developers.home-assistant.io/docs/automations)).
