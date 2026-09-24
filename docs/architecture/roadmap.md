# Reduction roadmap

The architecture documents and ADRs say what ha-lite keeps and why. GitHub
issues track the work that gets there. This page connects the two: for each
wave it states what has to be true before the wave starts, what has to be true
for it to be finished, and which issue carries every block that is still open.

A pull request that finishes a block updates this page in the same change, so
the repository alone answers what is done, what is intentionally retained and
what is still to do.

## Where things stand

| Wave | Scope | Epic | Status |
|---|---|---|---|
| 1 | Frontend, Lovelace and browser-product bootstrap | — | Done |
| 2 | Automation and Script | — | Done |
| 3 | Remaining Home Assistant product layers | [#16] | Done |
| 4 | Explicit retained integration closure | [#17] | Done, integration deletion reversed |
| 5 | Persistence, configuration and runtime composition | [#18] | Done |
| — | Integration catalog restored | — | Done; 14 integrations wait for decoupling, 56 are out by design |

[#15] is the umbrella epic. Waves 3 and 4 overlap on purpose: the closure (#24)
was built during Wave 3 so that each Wave 3 cut could be checked against it.

## Wave 1 — headless bootstrap

**Done.** `frontend` and `lovelace` are physically absent. Bootstrap has no
frontend stage, no critical integration, no Lovelace storage preload and no
browser launch, and `config` no longer registers a panel. The plan and its
checkpoints are in [deletion-wave-1.md](deletion-wave-1.md); the reasoning is
ADR 0007.

Deferred rather than done:

- Recovery mode had its product entries removed but was never redefined as a
  headless recovery path. [#30] did that later; ADR 0016.
- `map_tiles` and `my`, listed as likely Wave 1 deletions, went in [#22].

## Wave 2 — automation and script

**Done.** `automation` and `script` are physically absent, together with the
`config` API sections that edited them. ADR 0002.

`blueprint` was the one planned Wave 2 deletion that had to wait: `template`
still imported it. [#19] removed both together in Wave 3, so the exception is
closed.

## Wave 3 — remaining product layers ([#16])

**Entry:** Waves 1 and 2 done; the closure gate running in CI (ADR 0010).

**Exit:**

- none of the product components below remains in the tree;
- every domain the wave decided to keep is a root with a CI job, or a reviewed
  `accepted_transitive` entry;
- the MCP control surface is protected by a test that runs with the removed
  voice components absent (ADR 0009).

| Block | Issue | Status |
|---|---|---|
| Automation-adjacent helpers (`input_*`, `counter`, `timer`, `schedule`), `template`, `blueprint`, `cloud`, Alexa, Google Assistant | [#19] | Done |
| Scenes, groups and the derived location domains (`person`, `zone`, `device_tracker`, `sun`) | [#20] | Done — all kept; ADR 0002, ADR 0010 |
| History, logbook and energy | [#21] | Done |
| `onboarding`, `default_config`, `file_upload`, `my`, `map_tiles`, `search`, and the bootstrap defaults `analytics`, `labs`, `brands`, `hardware` | [#22] | Done — ADR 0016 |
| Assist and voice presentation, `media_source`, `ai_task` | [#23] | Done — MCP guarded by `tests/ha_lite/test_mcp_headless.py`; `media_source` later restored |

## Wave 4 — explicit integration closure ([#17])

**Entry:** the closure is authoritative and gated in CI ([#24], done). Bulk
deletion additionally waits for the retained integrations to be decoupled from
product conveniences ([#25], done) and for an OAuth/reauth lifecycle to be
protected in CI ([#26], done).

**Done, then reversed for the integrations.** #27 deleted every component the
closure did not reach, which took Home Assistant's integration catalog with
the product layers. That was never the goal, and ADR 0020 brought the catalog
back; see [the catalog restored](#the-catalog-restored). The closure, its gate
and the decoupling work of #25 and #26 stand.

**Exit:**

- the tree contains the retained closure and nothing else — the closure report
  lists no deletion candidates;
- CI rejects a component that is reintroduced outside the closure;
- the capability-at-risk list has been worked, not just read (ADR 0011);
- every scope-matrix row still marked INVESTIGATE that names a component the
  closure does not reach — today only HomeKit controller — has been promoted
  to a root or accepted as a deletion;
- the size report has been run before and after, and the result is recorded in
  the README.

| Block | Issue | Status |
|---|---|---|
| Generate the authoritative retained closure | [#24] | Done — `script/ha_lite_closure.py`, [retained-closure.md](retained-closure.md) |
| Decouple retained integrations from product conveniences (MQTT, Matter, `usb`) | [#25] | Done — `hassio` and `backup` left the closure |
| OAuth/cloud integration lifecycle anchor in CI | [#26] | Done — Miele; ADR 0017 |
| Physically remove the unselected integrations | [#27] | Done — 1,379 components deleted; capability-at-risk list and HomeKit controller settled in [retained-closure.md](retained-closure.md#wave-4) |

Found on the way: `demo` was outside the closure, but about twenty retained
test suites use it — as a stand-in domain in config-entry tests, and as the
platform the `media_player`, `group` and `camera` tests set up — and
`kitchen_sink` sits behind `group`'s lock tests. #27 made both roots in a
`test_fixtures` category, pruned to the retained domains, with their own CI
job. HomeKit controller, the last scope-matrix row the closure did not reach,
was not promoted: Matter covers the same local-device ground.

## Wave 5 — persistence, configuration, runtime composition ([#18])

**Entry:** Wave 4 done, so the runtime being simplified is the one ha-lite
actually ships. Wave 5 does not block Waves 3 and 4, and #30 landed early
because removing onboarding in #22 needed its replacement.

**Done.** Every exit criterion below holds.

**Exit:**

- a documented persistence contract, with Recorder removed or reduced to what
  that contract names;
- YAML and dependency installation match the retained runtime rather than the
  full Home Assistant distribution;
- a fresh and a broken installation can be initialised, inspected and repaired
  with no browser product.

| Block | Issue | Status |
|---|---|---|
| Minimal persistence contract; retire Recorder product semantics | [#28] | Done — Recorder removed; ADR 0018 supersedes ADR 0004 |
| Configuration, YAML loading and dependency installation | [#29] | Done — YAML kept as input, the tree's requirements ship with the distribution, hassfest, requirements and mypy gated in CI; ADR 0019 |
| Headless bootstrap, recovery and administrative control | [#30] | Done — `hass --script owner`, recovery as an API path; ADR 0016 |

## The catalog restored

**Done.** ADR 0020 records the decision: the tree carries Home Assistant's
integration catalog, and what ha-lite removes is a product layer. 1,218
components deleted in Wave 4 came back, together with `media_source`;
`trace`, which only serves automations and scripts, joined the excluded layers. The
closure gate now rejects an excluded product layer in the tree and an import,
from anywhere, of a component that is gone. The `catalog` CI job runs every
catalog suite in ten shards.

Compat modules answer what integrations ask a removed layer, without being
integrations:
- `automation.py`, `script.py` and `onboarding.py` brought back 35 components,
  among them Sonos, Google Cast, TP-Link, UniFi Protect, Ring and SmartThings;
- `cloud.py`, `default_config.py`, `counter.py` and the `input_*` modules
  brought back 22 more, among them HomeKit Bridge, go2rtc, Netatmo, Withings
  and the `derivative`, `integration` and `min_max` helpers.

`cloud` then came back as an integration reduced to Nabu Casa's account
linking, which brought August, Yale and Watts with it.

**Still open:** 70 integrations and 28 virtual integrations pointing at them.
[retained-closure.md](retained-closure.md#what-is-still-out) lists them in two
groups:

- 56 are out by design: speech and AI, Recorder statistics, backup agents,
  Home Assistant's own hardware and `intent_script`.
- 14 wait for a decoupling:
  - `hassio` and Home Assistant's own hardware: ESPHome, ZHA, Z-Wave JS and
    OTBR;
  - `file_upload` and `frontend`: KNX, Insteon, Velbus and others.

No issue carries this yet.

## Open questions without an issue

Shipping the core and the integrations as separate, version-locked packages
is proposed in ADR 0021; [split-distribution.md](split-distribution.md) has the
plan. It gets an issue when the proposal is accepted.

The scope matrix still marks the area, floor and label registries and the REST
API as INVESTIGATE. Both are core code rather than components, so the closure
cannot delete them and no wave is blocked on them. They get an issue when a
concrete reduction is proposed.

## Size checkpoints

Measured with `script/ha_lite_size_report.py` on the tracked files of each
checkpoint. The README carries the current numbers.

| Checkpoint | Tracked files | Product Python under `homeassistant/` | Python tests | Component domains |
|---|---:|---:|---:|---:|
| Before Wave 1 (upstream 2026.9.3, not reproducible here) | 27,507 | 10,028 files / 51.36 MB | 8,269 files / 67.45 MB | 1,509 |
| After Waves 1–2 (root commit `b9b89717`) | 27,437 | 10,004 files / 51.14 MB | 8,247 files / 67.07 MB | 1,482 |
| During Wave 3 (after #19, #20, #21, #24) | 27,023 | 9,844 files / 49.63 MB | 8,094 files / 64.12 MB | 1,465 |
| After #23 (voice, media browser, AI tasks) | 26,894 | 9,792 files / 49.26 MB | 8,047 files / 63.58 MB | 1,458 |
| After Wave 3 (#22, #25, #30) | 26,824 | 9,764 files / 49.09 MB | 8,021 files / 63.20 MB | 1,448 |
| After Wave 4 (#26, #27) | 3,202 | 979 files / 8.75 MB | 1,094 files / 17.31 MB | 91 |
| After Wave 5 (#28, #29) | 3,069 | 925 files / 8.06 MB | 1,019 files / 15.60 MB | 90 |
| After the catalog restore (#49, #50) | 22,729 | 8,395 files / 38.92 MB | 6,779 files / 46.89 MB | 1,289 |
| After the compat modules (#51) | 24,216 | 8,799 files / 41.97 MB | 7,138 files / 50.84 MB | 1,324 |
| After the cloud and helper compat modules | 24,689 | 8,981 files / 43.27 MB | 7,283 files / 52.81 MB | 1,342 |
| After account linking | 24,858 | 9,023 files / 43.40 MB | 7,317 files / 53.08 MB | 1,346 |

The first row was measured before the repository's history begins: the root
commit is a squashed import taken after Waves 1 and 2, so that snapshot cannot
be regenerated from this repository. Every later row can.

The component-domain column counts directories that contain Python. The
closure counts every directory with a manifest, which is 20 more today.

The numbers barely moved until Wave 4. Product layers are a small part of
the tree; roughly 94% of the Python under `homeassistant/` was component code,
almost all of it integrations the closure did not reach. Wave 4 deleted them,
and the catalog restore brought them back: they are what ha-lite is for, not
what it set out to remove.

[#15]: https://github.com/sebastian-software/ha-lite/issues/15
[#16]: https://github.com/sebastian-software/ha-lite/issues/16
[#17]: https://github.com/sebastian-software/ha-lite/issues/17
[#18]: https://github.com/sebastian-software/ha-lite/issues/18
[#19]: https://github.com/sebastian-software/ha-lite/issues/19
[#20]: https://github.com/sebastian-software/ha-lite/issues/20
[#21]: https://github.com/sebastian-software/ha-lite/issues/21
[#22]: https://github.com/sebastian-software/ha-lite/issues/22
[#23]: https://github.com/sebastian-software/ha-lite/issues/23
[#24]: https://github.com/sebastian-software/ha-lite/issues/24
[#25]: https://github.com/sebastian-software/ha-lite/issues/25
[#26]: https://github.com/sebastian-software/ha-lite/issues/26
[#27]: https://github.com/sebastian-software/ha-lite/issues/27
[#28]: https://github.com/sebastian-software/ha-lite/issues/28
[#29]: https://github.com/sebastian-software/ha-lite/issues/29
[#30]: https://github.com/sebastian-software/ha-lite/issues/30
