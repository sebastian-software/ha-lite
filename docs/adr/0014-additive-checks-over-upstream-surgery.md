# ADR 0014: Add checks in our own files rather than edit upstream ones

- Status: Accepted

## Context

ha-lite has two goals that pull against each other. It must protect itself
against its own reductions, which argues for more checks and tighter tests. And
it must keep pulling updates from Home Assistant Core affordable, which argues
for touching upstream files as little as possible — every edited line is a
conflict on every future update, forever.

ADR 0003 already says to prefer deletion over compatibility and not to
reorganize retained code for aesthetics. It does not say what to do about code
that is neither out of scope nor wrong, just wasteful. ADR 0008 allows removing
tests when the behaviour they protect leaves ha-lite's scope, and says nothing
about tests that are redundant while the behaviour stays.

A concrete case forced the question. `tests/components/air_quality` holds 14,527
cases, 45% of all tests across the fifteen device-class components. Measuring
showed that 3,502 of them produce byte-identical statement *and* branch coverage
of `helpers/trigger.py` and `helpers/condition.py`: the other 11,025 re-run the
same shared factory logic once per device class, because the component is a
declaration table and the logic lives in five shared factories.

Trimming that is tempting and would be wrong. Those files are upstream, they
change upstream, and a rewritten parametrize block conflicts on every single
update while buying nothing but wall-clock.

Meanwhile the same investigation found something the 14,527 tests do not cover
at all. A trigger declares its targets twice — `_domain_specs` in `trigger.py`,
which filters at runtime, and `target.entity` in `triggers.yaml`, which
`websocket_api` reports through `triggers/target`. Nothing compares them.
Removing the `input_*` helpers cleaned the Python side and left four deleted
domains in seven YAML targets, so capability discovery advertised entities that
no longer existed. hassfest did not catch it; neither did any test.

## Decision

Protect ha-lite by adding checks in files ha-lite owns, not by editing upstream
files.

A new invariant belongs in `script/ha_lite_*.py` with a `--check` mode, a test
in `tests/script/`, and a step in the `static-sanity` CI job. That is the shape
`ha_lite_closure.py` already established and `ha_lite_trigger_targets.py` now
follows. Such a file has no upstream counterpart, so it never conflicts.

Do not restructure upstream tests to remove redundancy while the behaviour they
cover stays in scope. Redundancy costs CI time, which is cheap and can be bought
back with parallelism; divergence costs every future update, which is not.
This extends ADR 0008: scope removal justifies deleting a test, efficiency does
not.

Where an upstream file must change to make a reduction work, keep the change as
small as the reduction needs, as ADR 0006 already requires for integrations.

## Consequences

Redundant upstream tests stay. `air_quality` keeps all 14,527 cases, and the
device-class CI matrix runs with `-n auto` instead. Measured on CI, that job
goes from 7:53 to 4:59 and the whole run from 8:56 to 6:12. Locally the same
change was worth 3.5x rather than 1.6x, so these tests do not scale with cores
the way a CPU-bound suite would -- they are event-loop bound, and each xdist
worker pays to import Home Assistant again. Parallelism buys back less than it
looks like it should, which weakens the argument above without changing it:
divergence still costs more, every update, forever.

The measurement that showed the redundancy is recorded here rather than acted
on, so a future reader does not have to rediscover it before deciding again.

ha-lite accumulates its own checks alongside the upstream suite instead of
reshaping it. Each one is a file that did not exist upstream, which is the
property that makes it free to maintain across updates.

The first two such checks each found a real defect on their first run — an
irreproducible closure artifact, and seven stale YAML targets left by #19 — so
the pattern pays for itself rather than being hygiene.

This does not license adding checks freely. Each one runs on every commit and
has to be worth that, which means it should encode an invariant a reduction can
plausibly break, not a general opinion about quality.
