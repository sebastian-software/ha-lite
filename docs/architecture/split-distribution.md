# Splitting the distribution

ADR 0021 proposes shipping ha-lite as a core package plus one package per
integration, all built from this repository and released together. This
document is the plan behind it: what goes where, which interfaces exist between
the packages, and in which order the steps can land. It is a proposal; nothing
here is implemented yet.

[upstream-integration-api.md](upstream-integration-api.md) explains why Home
Assistant itself ships everything in one package and offers no stable API for
integrations. The plan below does not need one.

## The problem

ADR 0020 keeps Home Assistant's integration catalog in the tree, and the
distribution follows the tree. Installing ha-lite installs the 1,268
catalog members, 1,157 integrations with code and 111 virtual ones: 34.9 MB of
Python in 7,999 files. A deployment uses a handful of them.

At runtime this costs almost nothing. The loader imports an integration only
when it is set up, and requirements are installed on first use (ADR 0019). The
cost is in distribution and review. Whoever installs ha-lite receives, and is
responsible for, code for devices they will never own.

## What stays

- **One repository and one CI.** Every integration keeps running its suite
  against the core it ships with. That lockstep is what showed, in #50 and
  #51, exactly what breaks when a layer goes. Moving the catalog to its own
  repository would lose it.
- **Upstream's import paths.** An integration stays
  `homeassistant.components.<domain>`, so upstream code, tests and imports
  between integrations keep working without edits (ADR 0014).
- **Custom integrations.** `custom_components/` loads as it does today.

## The interface as it is

The interface between the core and an integration is whatever the
integration imports. Measured over the 1,268 catalog integrations in this
tree:

| What they import | Count |
|---|---|
| Core modules outside `homeassistant/components` | 95 modules, 785 distinct names |
| Components of the protected core (entity domains, `diagnostics`, `bluetooth` and others) | 63 components, 660 distinct names |
| Compat modules (`automation`, `script`, `onboarding`, `cloud` and seven that name a domain) | 11 |
| Other catalog integrations | 31 integrations import one, most often `ffmpeg` (15) and `mjpeg` (7) |

The most used core modules:

| Module | Integrations |
|---|---|
| `homeassistant.core` | 1,157 |
| `homeassistant.const` | 1,129 |
| `homeassistant.helpers.entity_platform` | 1,027 |
| `homeassistant.config_entries` | 862 |
| `homeassistant.helpers.typing` | 749 |
| `homeassistant.helpers.device_registry` | 722 |
| `homeassistant.exceptions` | 693 |
| `homeassistant.helpers.update_coordinator` | 550 |
| `homeassistant.helpers.aiohttp_client` | 372 |
| `homeassistant.util` | 332 |

About 1,450 names in total. That is not an API anybody designed; it is the
whole of Home Assistant's helper layer. It is why the plan locks versions
instead of promising stability, and why a stable API is a separate, later
question (level 3 below).

Integrations barely depend on each other. Only 31 of the 1,268 import another
catalog integration, so a package rarely needs another integration package.

## The packages

| Package | Contents | Size |
|---|---|---|
| `ha-lite` (core) | `homeassistant/` without the catalog directories; the 98 components of the protected core; the compat modules; the generated discovery index (`homeassistant/generated/`); brands; the 111 virtual integrations, each a manifest and at most a one-line module | 8.4 MB of Python in about 970 files; 51 requirements |
| `ha-lite-<domain>`, one per catalog integration with code (1,157) | `homeassistant/components/<domain>/`: code, `manifest.json`, `services.yaml`, `strings.json`, translations and icons | median 18 KB; the largest, UniFi Protect, 0.39 MB |
| `ha-lite-all` | nothing; it depends on every integration package | — |

`ha-lite-all` gives the installation that exists today, for deployments that
want everything present and nothing installed at runtime.

The distribution in `pyproject.toml` is still named `homeassistant`, as
upstream's is. It has to be renamed before anything is published, so that it
never collides with Home Assistant's own package.

## Interfaces

The plan has three levels. Only the first is needed to split the
distribution.

### Level 1: the distribution contract

**Versions are locked.** An integration package has the core's version, and
it requires exactly that core:

```text
ha-lite-sonos 2026.9.3
  Requires-Dist: ha-lite == 2026.9.3
  Requires-Dist: soco == 0.31.2            # from the manifest's requirements
  Requires-Dist: ha-lite-plex == 2026.9.3  # a catalog integration it imports
```

That is what the monorepo already guarantees: every integration is tested
against the core in the same commit. The package metadata states it. No
integration package is ever installed against a different core.

**Packages install into the core's package directory.** An integration wheel
contains `homeassistant/components/<domain>/` and nothing above it. The loader
resolves built-in integrations by looking for `<domain>/manifest.json` under
`homeassistant.components.__path__` (`Integration.resolve_from_root` in
`homeassistant/loader.py`). So an installed package is found the way a
built-in integration is found today, without a change to the loader. The
alternative, a separate namespace found through entry points, would change
every import path of every integration and its tests.

**The discovery index stays complete.** The core ships
`homeassistant/generated/` for the whole catalog: config flows and the
zeroconf, DHCP, SSDP, Bluetooth and USB matchers. A Sonos speaker on the
network is recognised even when `ha-lite-sonos` is not installed, and the
core can say which package handles it.

**A missing integration is installed like a missing requirement.** The loader
does not cache an integration it cannot find (`async_get_integrations` in
`homeassistant/loader.py`), so a package installed at runtime is found on the
next attempt. The requirements manager already installs an integration's
requirements before setup (`async_get_integration_with_requirements` in
`homeassistant/requirements.py`). It gains one step before that. If the domain
is in the index but not installed, it installs `ha-lite-<domain>` at the
core's version.

- Where pip is allowed, a discovered Sonos speaker's config flow installs
  the package and continues.
- With `--skip-pip` nothing is installed. A repair issue names the package,
  and the operator installs it with `pip install ha-lite-sonos==2026.9.3`.
- An explicit command, `hass --script install sonos`, installs the right
  version without starting a flow.

**The core checks what it loads.** An integration package whose version
differs from the core's is not loaded: the loader reads the installed
distribution's version, logs the mismatch, and treats the integration as
missing, which leads to the install path above. A partial upgrade can
therefore never run code built for another core.

### Level 2: make the code interface visible

A gate in the style of `script/ha_lite_closure.py` records the names the
catalog imports from the core, the roughly 1,450 above, in a generated file.
It fails when:

- a catalog integration starts importing a core name that is not in the file;
- the core removes or renames a name that is in the file.

This promises nothing about stability. What it gives is visibility. A change
to the interface becomes a reviewed diff rather than something noticed when
a package breaks. And an upstream update (ADR 0003) shows exactly how much of
the interface it moved. That number is the evidence level 3 would need.

### Level 3: a stable, versioned API — not now

A stable API would let packages built outside this repository, against a
different core version, keep working. It needs:

- a declared surface much smaller than 1,450 names;
- semantic versioning of that surface;
- deprecation windows;
- shims for every change upstream makes to it.

Every upstream update would first have to be translated into that API. Home
Assistant has chosen not to pay that cost; see
[upstream-integration-api.md](upstream-integration-api.md). ha-lite has less
reason to: its catalog is upstream's, and it is built here. Level 3 becomes
a question only if third parties want to publish integration packages that
this repository does not build.

## Build, test, release

- **Build.** A script, `script/ha_lite_build_packages.py`, builds the core
  wheel and one wheel per catalog integration from the same commit. It
  generates each integration's package metadata from its manifest:
  - the name;
  - the core as a dependency;
  - the requirements;
  - integration packages for the manifest's `dependencies` and for module-level
    imports of other catalog integrations. The closure tool already computes
    those edges.
- **Test.** The existing jobs stay as they are and test the code. A new
  packaging job installs the core wheel and a sample of integration wheels
  into a clean environment and runs those integrations' suites against the
  installed packages. That proves the packaging, not the code. The sample
  should include one integration with cross-package dependencies, such as
  `sonos` through `plex` and `cast`.
- **Release.** Every release publishes the core, every integration package
  and `ha-lite-all` together, under one version.

## Steps

1. Rename the distribution. Add the build script and the packaging job.
   Nothing changes for users: the full package is still what gets installed.
2. Add the version check and install-on-demand to the loader and the
   requirements manager, behind the existing pip switch, with tests.
3. Publish the core, the integration packages and `ha-lite-all`. Document
   both installations: everything, or core plus what is needed.
4. Add the level-2 interface gate.

Each step is useful alone. Step 1 already shows whether the packages build
and install, before any user depends on them.

## Open questions

- **Where packages are published.** PyPI would host about 1,250 projects per
  version under an `ha-lite-` prefix; its policies on project count and
  naming need checking first. The alternative is a package index hosted with
  the project's releases.
- **Virtual integrations** are manifests that point at another integration.
  They are small enough to stay in the core with the discovery index, which
  keeps the brand pages and discovery complete.
- **Translations and brands.** Translations belong to the integration
  package. Brands stay in the core, because the index uses them.
- **The protected core.** It stays one package. Its entity domains are the
  interface integrations build on; splitting them would give no user a
  smaller installation.
