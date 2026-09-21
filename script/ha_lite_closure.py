#!/usr/bin/env python3
"""Compute the ha-lite retained dependency closure.

The closure answers one question: which integration domains must survive so the
retained runtime still works? Everything outside it is a deletion candidate.

Two graphs feed the closure, as `docs/architecture/overview.md` requires:

- declared edges from `manifest.json`
- actual edges from Python imports, parsed with `ast`

Import edges are classified by strength. Only *hard* edges (manifest
`dependencies` and module-level imports) grow the closure, because a
function-local import is coupling that can be patched out without touching the
importing component's module graph. Soft edges are reported separately so that
latent coupling stays visible instead of silently widening the closure.

Roots and accepted transitive members live in `ha_lite_closure_config.json`
next to this script. A domain that enters the closure without being either is a
finding: someone added coupling from retained code into an unreviewed
component.

    python3 script/ha_lite_closure.py            # human-readable report
    python3 script/ha_lite_closure.py --check    # CI gate, non-zero on findings
    python3 script/ha_lite_closure.py --json     # machine-readable closure
"""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict, deque
import json
from pathlib import Path
import sys
from typing import override

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "homeassistant" / "components"
CONFIG = Path(__file__).resolve().parent / "ha_lite_closure_config.json"

MODULE_PREFIX = "homeassistant.components."
COMPONENTS_PACKAGE = MODULE_PREFIX.rstrip(".")
# Core is always loaded, so anything it imports is required unconditionally.
CORE = "<core>"

# Only these grow the closure; every other kind is soft. See the module docstring.
HARD_KINDS = ("dependencies", "import_runtime")


class Edge:
    """One directed domain-to-domain dependency and where it comes from."""

    __slots__ = ("kind", "source", "target", "via")

    def __init__(self, source: str, target: str, kind: str, via: str) -> None:
        """Store one edge and the file or manifest that declares it."""
        self.source = source
        self.target = target
        self.kind = kind
        self.via = via

    @property
    def hard(self) -> bool:
        """Return whether this edge is strong enough to grow the closure."""
        return self.kind in HARD_KINDS


def domain_of_module(module: str | None) -> str | None:
    """Return the component domain a dotted module path belongs to."""
    if not module or not module.startswith(MODULE_PREFIX):
        return None
    rest = module[len(MODULE_PREFIX) :]
    return rest.split(".", 1)[0] if rest else None


class ImportCollector(ast.NodeVisitor):
    """Collect component imports, tagged by how strongly they bind.

    Module-level imports bind hard. Imports inside a function body are deferred
    and can be removed without restructuring the module. Imports guarded by
    `TYPE_CHECKING` never execute at all.
    """

    def __init__(self, domain: str, via: str) -> None:
        """Prepare to collect the component edges declared by one file."""
        self.domain = domain
        self.via = via
        self.edges: list[Edge] = []
        self._function_depth = 0
        self._type_checking_depth = 0

    def _kind(self) -> str:
        if self._type_checking_depth:
            return "import_typing"
        if self._function_depth:
            return "import_deferred"
        return "import_runtime"

    def _record(self, modules: list[str | None]) -> None:
        kind = self._kind()
        for module in modules:
            target = domain_of_module(module)
            if target and target != self.domain:
                self.edges.append(Edge(self.domain, target, kind, self.via))

    @override
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track that imports below this point are function-local."""
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    @override
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track that imports below this point are function-local."""
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    @override
    def visit_If(self, node: ast.If) -> None:
        """Track `TYPE_CHECKING` blocks so their imports are not counted."""
        test = node.test
        is_type_checking = (
            isinstance(test, ast.Name) and test.id == "TYPE_CHECKING"
        ) or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")
        if not is_type_checking:
            self.generic_visit(node)
            return
        self._type_checking_depth += 1
        for child in node.body:
            self.visit(child)
        self._type_checking_depth -= 1
        for child in node.orelse:
            self.visit(child)

    @override
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Record an absolute `from ... import ...` edge."""
        # A relative import cannot leave its own component.
        if node.level:
            return
        if node.module == COMPONENTS_PACKAGE:
            # `from homeassistant.components import person` names the domain in
            # the import list, not in the module path.
            self._record([f"{MODULE_PREFIX}{alias.name}" for alias in node.names])
            return
        self._record([node.module])

    @override
    def visit_Import(self, node: ast.Import) -> None:
        """Record a plain `import ...` edge."""
        self._record([alias.name for alias in node.names])


def collect_edges() -> tuple[set[str], list[Edge]]:
    """Return every component domain plus every dependency edge between them."""
    domains: set[str] = set()
    edges: list[Edge] = []

    for directory in sorted(p for p in COMPONENTS.iterdir() if p.is_dir()):
        manifest = directory / "manifest.json"
        # A manifest is what makes a directory an integration. Anything else
        # under components/ is build output such as __pycache__, which exists
        # in a working checkout but not in a fresh clone.
        if not manifest.is_file():
            continue

        domain = directory.name
        domains.add(domain)

        via = str(manifest.relative_to(ROOT))
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        for key in ("dependencies", "after_dependencies"):
            edges.extend(
                Edge(domain, dep, key, via)
                for dep in data.get(key, [])
                if dep != domain
            )

        for path in sorted(directory.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError, UnicodeDecodeError:
                continue
            collector = ImportCollector(domain, str(path.relative_to(ROOT)))
            collector.visit(tree)
            edges.extend(collector.edges)

    for path in sorted(ROOT.joinpath("homeassistant").rglob("*.py")):
        if "components" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError, UnicodeDecodeError:
            continue
        collector = ImportCollector(CORE, str(path.relative_to(ROOT)))
        collector.visit(tree)
        edges.extend(collector.edges)

    return domains, edges


def build_closure(
    roots: set[str], domains: set[str], edges: list[Edge]
) -> tuple[set[str], dict[str, Edge]]:
    """Walk hard edges from the roots, recording why each domain was pulled in."""
    adjacency: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        if edge.hard:
            adjacency[edge.source].append(edge)

    reached = {root for root in roots if root in domains}
    queue = deque([*sorted(reached), CORE])
    reason: dict[str, Edge] = {}

    while queue:
        current = queue.popleft()
        for edge in sorted(adjacency[current], key=lambda e: (e.target, e.via)):
            if edge.target in domains and edge.target not in reached:
                reached.add(edge.target)
                reason[edge.target] = edge
                queue.append(edge.target)

    return reached, reason


def collect_platform_providers(
    platforms: list[str], domains: set[str]
) -> dict[str, list[str]]:
    """Return the domains providing each runtime-resolved platform.

    A platform file is loaded by name through `async_get_platform`, never
    imported, so none of this shows up in the edge graph. Providing a platform
    is not a dependency either: the runtime dispatches to whatever is there.
    Deleting a provider therefore removes a capability without breaking an
    import, which is exactly what the closure alone cannot warn about.
    """
    providers: dict[str, list[str]] = {}
    for platform in platforms:
        providers[platform] = sorted(
            domain
            for domain in domains
            if (COMPONENTS / domain / f"{platform}.py").is_file()
        )
    return providers


def integration_type(domain: str) -> str:
    """Return a domain's manifest integration_type, or 'unknown'."""
    manifest = COMPONENTS / domain / "manifest.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return "unknown"
    value = data.get("integration_type", "unknown")
    return value if isinstance(value, str) else "unknown"


def load_config() -> dict:
    """Return the checked-in roots and accepted transitive members."""
    config: dict = json.loads(CONFIG.read_text(encoding="utf-8"))
    return config


def analyze() -> dict:
    """Compute the closure and everything the report and the gate need."""
    config = load_config()
    roots: set[str] = set()
    for members in config["roots"].values():
        roots.update(members)
    accepted: dict[str, dict] = config["accepted_transitive"]

    domains, edges = collect_edges()
    closure, reason = build_closure(roots, domains, edges)

    missing_roots = sorted(roots - domains)
    unreviewed = sorted(closure - roots - set(accepted))
    stale_accepted = sorted(set(accepted) - closure)

    # Soft edges that would widen the closure if they ever hardened.
    latent: list[Edge] = [
        edge
        for edge in edges
        if not edge.hard and edge.source in closure and edge.target not in closure
    ]

    # Capabilities the retained runtime can dispatch to, whose providers the
    # closure cannot see. These do not grow the closure; they are a deletion
    # warning list.
    platforms: list[str] = config["cross_cutting_platforms"]
    providers = collect_platform_providers(platforms, domains)
    at_risk: dict[str, dict] = {}
    for platform, domain_list in providers.items():
        for domain in domain_list:
            if domain in closure:
                continue
            entry = at_risk.setdefault(
                domain, {"integration_type": integration_type(domain), "platforms": []}
            )
            entry["platforms"].append(platform)

    return {
        "domains": domains,
        "edges": edges,
        "roots": roots,
        "accepted": accepted,
        "closure": closure,
        "reason": reason,
        "missing_roots": missing_roots,
        "unreviewed": unreviewed,
        "stale_accepted": stale_accepted,
        "latent": latent,
        "platform_providers": providers,
        "capability_at_risk": at_risk,
    }


def as_json(result: dict) -> dict:
    """Shape the closure as the allowlist that Wave 4 deletion consumes."""
    reason = result["reason"]
    return {
        "closure": sorted(result["closure"]),
        "roots": sorted(result["roots"]),
        "accepted_transitive": sorted(set(result["accepted"]) & result["closure"]),
        "deletion_candidates": sorted(result["domains"] - result["closure"]),
        "pulled_in_by": {
            domain: {
                "source": reason[domain].source,
                "kind": reason[domain].kind,
                "via": reason[domain].via,
            }
            for domain in sorted(reason)
        },
        "findings": {
            "unreviewed_closure_members": result["unreviewed"],
            "stale_accepted_entries": result["stale_accepted"],
            "missing_roots": result["missing_roots"],
        },
        # Not part of the closure. Consult before bulk deletion: removing these
        # drops a runtime capability without breaking any import.
        "capability_at_risk": {
            domain: result["capability_at_risk"][domain]
            for domain in sorted(result["capability_at_risk"])
        },
    }


def print_report(result: dict) -> None:
    """Write the human-readable report to stdout."""
    domains = result["domains"]
    closure = result["closure"]
    reason = result["reason"]
    accepted = result["accepted"]

    print("# ha-lite retained dependency closure\n")
    print("| Metric | Count |")
    print("| --- | ---: |")
    print(f"| Component domains in tree | {len(domains):,} |")
    print(f"| Declared roots | {len(result['roots']):,} |")
    print(f"| Retained closure | {len(closure):,} |")
    print(f"| Deletion candidates | {len(domains) - len(closure):,} |")

    pulled = sorted(closure - result["roots"])
    print(f"\n## Transitively required ({len(pulled)})\n")
    print("| Domain | Pulled in by | Kind | Via | Status |")
    print("| --- | --- | --- | --- | --- |")
    for domain in pulled:
        edge = reason.get(domain)
        entry = accepted.get(domain, {})
        status = entry.get("status", "UNREVIEWED")
        src = edge.source if edge else "?"
        kind = edge.kind if edge else "?"
        via = edge.via if edge else "?"
        print(f"| `{domain}` | `{src}` | {kind} | `{via}` | {status} |")

    latent = result["latent"]
    if latent:
        by_target: dict[str, list[Edge]] = defaultdict(list)
        for edge in latent:
            by_target[edge.target].append(edge)
        print(f"\n## Latent coupling ({len(by_target)} domains outside the closure)\n")
        print("Soft edges only. These would widen the closure if they hardened.\n")
        print("| Outside domain | Reached from | Kind | Via |")
        print("| --- | --- | --- | --- |")
        for target in sorted(by_target):
            edge = min(by_target[target], key=lambda e: e.via)
            extra = len(by_target[target]) - 1
            suffix = f" (+{extra} more)" if extra else ""
            print(
                f"| `{target}` | `{edge.source}` | {edge.kind} | `{edge.via}`{suffix} |"
            )

    at_risk = result["capability_at_risk"]
    if at_risk:
        by_type: dict[str, list[str]] = defaultdict(list)
        for domain, info in at_risk.items():
            by_type[info["integration_type"]].append(domain)
        print(f"\n## Capability at risk ({len(at_risk)} domains)\n")
        print(
            "Providers of runtime-resolved platforms that sit outside the closure.\n"
            "They are reachable by name, not by import, so deleting them removes a\n"
            "capability without breaking anything. Consult before bulk deletion.\n"
        )
        print("| integration_type | Domains |")
        print("| --- | --- |")
        for kind in sorted(by_type):
            names = ", ".join(f"`{d}`" for d in sorted(by_type[kind]))
            print(f"| {kind} | {names} |")

    findings = result["unreviewed"] + result["stale_accepted"] + result["missing_roots"]
    print("\n## Findings\n")
    if not findings:
        print("None. The closure matches the reviewed configuration.")
        return
    for domain in result["unreviewed"]:
        edge = reason.get(domain)
        where = f"{edge.source} via {edge.via}" if edge else "unknown"
        print(
            f"- **unreviewed**: `{domain}` entered the closure from {where}. "
            "Patch the coupling out, or record it in ha_lite_closure_config.json."
        )
    for domain in result["stale_accepted"]:
        print(
            f"- **stale**: `{domain}` is accepted in the config but no longer "
            "reachable. Drop the entry."
        )
    for domain in result["missing_roots"]:
        print(f"- **missing root**: `{domain}` is declared a root but absent.")


def main() -> int:
    """Run the closure analysis in the mode the caller asked for."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--json", action="store_true", help="emit the machine-readable closure"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when the closure has unreviewed members",
    )
    parser.add_argument(
        "--write",
        type=Path,
        metavar="PATH",
        help="write the machine-readable closure to PATH",
    )
    args = parser.parse_args()

    result = analyze()
    payload = as_json(result)

    if args.write:
        args.write.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.write}", file=sys.stderr)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print_report(result)

    if args.check:
        findings = (
            result["unreviewed"] + result["stale_accepted"] + result["missing_roots"]
        )
        if findings:
            print(
                f"\nclosure check failed: {len(findings)} finding(s)", file=sys.stderr
            )
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
