# ADR 0020: Keep Home Assistant's integration catalog, remove only product layers

- Status: Accepted

## Context

ha-lite exists for the knowledge in Home Assistant's integrations: how to
discover, configure, observe and control real devices (ADR 0001). The waves
removed what Home Assistant adds on top as a product for people — the
frontend, automations, history, voice, cloud, the Supervisor — and kept the
runtime those integrations need.

Wave 4 (#27) went further than that. Its issue asked for "an explicit retained
integration set", and the only integrations any document named were the
anchors CI protected: Shelly, MQTT, Matter, Hue, Fronius, Modbus and Miele.
Every document called them *representative*. They stood for kinds of
integration — a local device, a protocol, a bridge, an energy device, a cloud
login — so that CI would protect the runtime contract all integrations share
(ADR 0006, ADR 0008). No larger set was ever written down, so the anchors
became the set. ADR 0010 made the closure the deletion authority, and the
closure did what it was told: it deleted the 1,379 components no anchor
reached, most device integrations among them.

That was a scope decision made by a reachability tool, the mistake ADR 0010
already warned about for `person`, `group` and `sun`. Reachability says what
the anchors need. It does not say what ha-lite is for.

## Decision

**The tree carries Home Assistant's integration catalog.** What ha-lite
removes is a product layer, not an integration. The removed layers are listed
under `excluded` in `script/ha_lite_closure_config.json`, grouped by what they
served, and the scope matrix gives the reason for each. A catalog integration
is kept as upstream ships it and loaded only when a user sets it up.

**The closure stays, and it now defines the protected core.** Roots are what
CI runs in full; the closure is what they need; every member that is not a
root has a reviewed `accepted_transitive` entry. The edge rules of ADR 0010
are unchanged:

| Kind | Grows the closure |
|---|---|
| `dependencies` | yes |
| `import_runtime` (module level) | yes |
| `after_dependencies` | no |
| `import_deferred` (function local) | no |
| `import_typing` (`TYPE_CHECKING`) | no |

Every component in the tree outside the closure is the **catalog**. That is
not a finding. `retained-closure.json` lists it.

**The gate checks the whole tree.** `script/ha_lite_closure.py --check` fails
on:

- an unreviewed closure member, a stale `accepted_transitive` entry or a
  missing root, as before;
- an **excluded** product layer that appears in the tree again;
- a **dangling** import, from any component or from core, of a component
  that is not in the tree. An integration that still imports a removed layer
  cannot load, so it stays out of the tree until it is decoupled, the way
  #25 decoupled MQTT and Matter from the Supervisor (ADR 0006).

**A removed layer can leave a compat module behind.** Many integrations
import a removed layer only to ask it one question:
- which automations and scripts use this entity, before they deprecate it;
- has the browser wizard finished, before a config flow adds a discovered
  device without asking;
- can Home Assistant Cloud give me a public webhook URL;
- what is the helper domain called that I list among the ones I support.

ha-lite answers such a question with a compat module: a single file directly
under `homeassistant/components/`, with no manifest, so it is not an
integration and cannot be set up. It gives the answer upstream gives when the
product integration is not loaded:
- `automation.py` and `script.py` find no automations or scripts;
- `onboarding.py` reports the instance as onboarded;
- `counter.py`, `default_config.py` and the `input_*` modules only name their
  domain and its constants.

The cloud question is the exception: `cloud` answers it itself, because it is
back as an integration (below). There is no subscription and no connection,
so integrations use their local webhook URL.

An import of a compat module is not dangling. A manifest never names one,
because a compat module is no integration: with pip allowed, setting up a
built-in integration resolves its `after_dependencies` too, and one that does
not resolve fails the setup. The gate therefore counts a manifest entry on a
missing domain or on a compat module as dangling. hassfest, which otherwise
wants every imported component declared in the manifest, accepts imports of
compat modules without that. Each module must be listed
under `compat_modules` in the closure config, with what it provides. A module
that is not listed there, or a listed module that is gone, is a finding.
That makes each compat module a reviewed decision rather than a way around
the dangling check. A compat module never grows into the product it stands
in for; an integration that needs more than an answer stays out.

**A removed layer can come back reduced to what serves devices.** Home
Assistant Cloud is a product: remote access, Alexa, Google Assistant, speech,
backup. One part of it serves devices: account linking. August, Yale and
Watts give their OAuth client credentials only to Nabu Casa, whose account
link server completes the sign-in without a Home Assistant Cloud account.
ha-lite's `cloud` is an integration reduced to that part:
- upstream's `account_link.py`, unchanged;
- its own `__init__.py`, which sets account linking up without building
  hass_nabucasa's `Cloud` and answers everything else as upstream does when
  nobody is logged in.

`cloud` is a catalog integration, not an excluded layer. Alexa, Google
Assistant and the rest of the cloud stay excluded.

A platform file that only a removed layer loads, such as WLED's
`analytics.py`, leaves with that layer, as logbook's describe platforms did.

**CI runs the catalog.** The `catalog` job runs every catalog suite, split
into ten shards by `script/ha_lite_catalog_shard.py`. Roots keep their own
jobs.

**Catalog tests are upstream tests.** They run as upstream ships them, and a
removed layer they lean on is replaced in ha-lite's own test support rather
than in each test (ADR 0014):

- `tests/helpers/automation_harness.py` answers setups of `automation` and
  `script` with the retained trigger, condition and action primitives. It
  shows each automation and script as an entity, the way the removed
  integrations did, so device-trigger tests keep working without the
  product. The compat modules' lookups answer from it, so a deprecation test
  finds the automations it set up;
- `tests/helpers/helper_harness.py` stands in for `input_boolean` (a toggle
  that restores its state), `intent_script` (speech and an action per intent)
  and the domain names of `input_number`, `input_select` and `counter`.

A test that only uses a removed layer as a tool the stand-ins do not cover is
adapted to a retained equivalent: a template sensor that disappears becomes a
state that is removed, a constant moves to the domain that defines it too. A
test that exercises a removed layer itself goes with the layer, as the entity
domains' `test_recorder.py` files went in Wave 5.

## Consequences

The restore brought back 1,219 components: the 1,218 that Wave 4 deleted and
whose code imports nothing that is gone, plus `media_source`, which Wave 3 had
removed with the voice stack although it serves camera, image and media
player entities. `trace` loaded too, but it records and debugs automations and
scripts, so it joined the excluded layers instead.

The compat modules brought back 57 more in two rounds:
- the first, with `automation`, `script` and `onboarding`, brought Sonos,
  Google Cast, TP-Link, UniFi Protect, Ring, SmartThings, Roborock, Yeelight,
  WiZ, WLED, Elgato, BTHome and HomeKit Device;
- the second, with `cloud` (then a compat module), `default_config`,
  `counter` and the `input_*` modules, brought HomeKit Bridge, go2rtc,
  Netatmo, Withings, OwnTracks, Rachio, the `derivative`, `integration`,
  `min_max`, `trend` and `bayesian` helpers, six more integrations and five
  virtual ones.

Account linking brought back four: `cloud` itself, August, Yale and Watts.

The tree holds 1,370 components: 98 in the closure and 1,272 in the catalog.

70 integrations and 28 virtual integrations pointing at them are still out.
`retained-closure.md` lists them in two groups:

- **Out by design** (56). Their purpose is a layer ha-lite removed:
  - speech and AI providers;
  - integrations that write to or read from Recorder's statistics;
  - backup agents;
  - Home Assistant's own hardware;
  - `intent_script`, which runs actions the way automations do.

  They leave with that layer.
- **Waiting for a decoupling** (14). They serve devices, and a coupling holds
  them back, not their purpose. Among them are ESPHome, ZHA, Z-Wave JS and
  KNX. Each needs a change of the #25 kind, or a compat module where the
  coupling is only a question.

The reduction is now in the product layers, not in the catalog. Product
Python goes from 8 MB back to 43 MB, and `requirements_all.txt` from 40
packages to 1,085; upstream's full catalog is 51 MB and 1,146. ADR 0019 records what that means for installation.

Upstream updates get cheaper. A curated update (ADR 0003) no longer has to
skip 1,379 deleted directories; it has to carry the excluded layers and the
decoupling patches, which are the changes ha-lite actually means.

Adding a root is still one decision with its CI job (ADR 0010's rule, which
this record keeps). Adding a catalog integration from upstream is copying it
in and regenerating; the gate and the catalog job cover it from then on.

ADR 0010 is superseded by this record. Its edge rules, its review of
transitive members and its rule that a root comes with a CI job stay in force
as restated here; what changed is that the closure no longer decides what may
be deleted.
