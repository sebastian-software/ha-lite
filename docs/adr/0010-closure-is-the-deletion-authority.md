# ADR 0010: Let the computed closure decide what may be deleted

- Status: Accepted

## Context

The first reduction waves selected deletion candidates from the scope matrix,
which classifies components by what they appear to be. That reading is a design
intent, not evidence. Directory names are a poor proxy for coupling: `cloud`
looked like an isolated product and turned out to be imported from
`helpers/config_entry_flow.py`, breaking the webhook flow of eight integrations
when it was removed.

Wave 4 proposes deleting over a thousand components at once. At that volume,
per-directory judgement does not scale and a single missed edge is expensive.

Home Assistant states coupling in two places, and they disagree often enough to
matter: `manifest.json` (`dependencies`, `after_dependencies`) and actual Python
imports. Neither alone is authoritative.

Not every edge binds equally. A module-level import cannot be removed without
restructuring the module. A function-local import, a `TYPE_CHECKING` import and
an `after_dependencies` entry can. Treating them alike is not merely imprecise,
it changes the answer: one deferred import of `cloud` in `http/__init__.py` — a
repairs check that ran when SSL was configured without an external URL — would
have pulled `cloud`, `alexa`, `google_assistant`, `tts`, `stt`, `backup` and
`assist_pipeline` into the retained set, inflating the closure from 78 domains
to 93 and making Wave 4 look far more constrained than it was.

## Decision

`script/ha_lite_closure.py` computes the retained closure from both graphs and
is the authority for deletion. A component may be deleted when it is reachable
from no declared root; the scope matrix records intent, the closure records
evidence.

Classify edges by strength. Only hard edges grow the closure:

| Kind | Grows the closure |
|---|---|
| `dependencies` | yes |
| `import_runtime` (module level) | yes |
| `after_dependencies` | no |
| `import_deferred` (function local) | no |
| `import_typing` (`TYPE_CHECKING`) | no |

Soft edges are reported as **latent coupling** rather than discarded: they are
what would widen the closure if they hardened.

Roots are declared in `script/ha_lite_closure_config.json` and every root has a
CI job in `.github/workflows/ha-lite-ci.yml`. What CI protects is what ha-lite
promises to keep working, so declaring a root and giving it test coverage are
one decision, not two.

This has been violated once already: ADR 0012 added fifteen roots without CI
jobs, leaving them protected from deletion but not from breakage. Adding a root
without a job is the failure mode to watch for, because nothing fails when it
happens.

Every domain that enters the closure without being a root needs a reviewed entry
in `accepted_transitive` carrying a status (`retained`, `adapter`,
`patch_required`), a reason and an issue. A domain reaching the closure without
one fails the check. So does an entry that is no longer reachable.

The check runs in CI, and the generated `docs/architecture/retained-closure.json`
is committed and verified against a fresh regeneration, so the reviewed allowlist
cannot drift from the tree.

## Consequences

New coupling from retained code into an unreviewed component is a build failure
rather than a discovery made months later. Widening the retained surface becomes
a reviewable change to a checked-in file with a written reason, not a side effect
of an import.

The closure is computed over what the tree contains, so it is only as good as
its definition of a component. An early version treated every directory under
`components/` as a domain, which made a working checkout and a fresh clone
disagree over `__pycache__`. Rules of this kind belong in
`tests/script/test_ha_lite_closure.py`, because the gate is only worth as much
as its own correctness, and those tests run in the `static-sanity` job.

Three such rules were missing and have since been added. Relative imports were
skipped, which is right inside a component and wrong in core: `bootstrap.py`
pre-imported `default_config` as `from .components import ...`, and with it
fifteen domains nobody had reviewed. Core's soft edges were left out of the
latent report, which hid that `helpers/service.py` calls into five entity
domains outside the closure. And an import of a component that is no longer in
the tree was invisible, because the walk only follows edges into domains that
exist; retained code doing that is now a **dangling** finding, however soft the
import. The first run found `core_config.py` still importing the deleted
`frontend`.

Wave 4 deleted everything the closure did not reach, so the tree and the
closure became the same set, and the gate now also works the other way round:
a component in the tree that the closure does not reach is an **outside**
finding. It was added without being declared a root, which is exactly the
coupling-free growth the closure exists to prevent.

The deletion also showed what reachability cannot see. Bootstrap sets up
integrations by name — its stages, its defaults, the generated
`configuration.yaml` — and those names are strings, not edges.
`tests/ha_lite/test_bootstrap_domains.py` checks each of them against the
committed closure. Retained upstream suites set up `demo` and `kitchen_sink`
by name too, so those two are roots in a `test_fixtures` category, pruned to
the retained domains: what CI runs has to exist, even when it is not runtime.

Reachability is necessary but not sufficient. It says nothing about capabilities
resolved by name at runtime; see ADR 0011.

It says nothing about scope either, and the closure must not be read as if it
did. Wave 3 tested each domain with "does a retained integration implement it?",
which is a fine question about *substrate* and the wrong one about everything
else. It kept `scene`, `device_tracker` and `zone` correctly, and it removed
`person`, `group` and `sun` — all three wrongly, because none of them is
implemented by a device integration and none of them needed to be. They were
restored after the fact.

The question that separates them is not who implements a domain but what the
domain answers: does it describe the physical world, and does the answer need
runtime state only this core holds? `person` and `group` fold live entity state,
so an external engine cannot reproduce them. `sun` needs no runtime state at
all, and is kept on the narrower ground that the core computes solar position
anyway. A domain reachable from nothing is a candidate for that question, not
an answer to it.
