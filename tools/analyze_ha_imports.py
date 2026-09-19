#!/usr/bin/env python3
"""Generate a component-level Home Assistant import graph.

Run this against a checkout that contains the Home Assistant source tree:

    python tools/analyze_ha_imports.py /path/to/core > dependency-graph.tsv

The script uses Python's AST rather than regex so multiline imports and aliases are
handled consistently. It intentionally captures only imports under
homeassistant.components.*; core/helper imports can be added as a second graph later.
"""

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path


PREFIX = "homeassistant.components."


def component_from_module(module: str | None) -> str | None:
    """Return the component domain referenced by a Home Assistant module."""
    if not module or not module.startswith(PREFIX):
        return None
    rest = module[len(PREFIX) :]
    return rest.split(".", 1)[0] if rest else None


def source_component(path: Path, components_root: Path) -> str:
    """Return the component domain that owns a Python source file."""
    return path.relative_to(components_root).parts[0]


def imports_for_file(path: Path) -> set[str]:
    """Return Home Assistant component domains imported by one Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if component := component_from_module(node.module):
                result.add(component)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if component := component_from_module(alias.name):
                    result.add(component)
    return result


def main() -> int:
    """Generate the component import graph and write it as TSV to stdout."""
    parser = argparse.ArgumentParser()
    parser.add_argument("core", type=Path, help="Home Assistant Core checkout")
    args = parser.parse_args()

    components_root = args.core / "homeassistant" / "components"
    if not components_root.is_dir():
        parser.error(f"not a Home Assistant Core checkout: {args.core}")

    edges: dict[str, set[str]] = defaultdict(set)
    for path in components_root.rglob("*.py"):
        src = source_component(path, components_root)
        edges[src].update(imports_for_file(path))

    lines = ["source\ttarget"]
    for src in sorted(edges):
        lines.extend(
            f"{src}\t{dst}"
            for dst in sorted(edges[src])
            if src != dst
        )
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
