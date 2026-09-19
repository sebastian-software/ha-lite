#!/usr/bin/env python3
"""Generate a component-level Home Assistant import graph.

Run this against a checkout that contains the Home Assistant source tree:

    python tools/analyze_ha_imports.py /path/to/core > dependency-graph.tsv

The script uses Python's AST rather than regex so multiline imports and aliases are
handled consistently. It intentionally captures only imports under
homeassistant.components.*; core/helper imports can be added as a second graph later.
"""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from pathlib import Path
import sys


PREFIX = "homeassistant.components."


def component_from_module(module: str | None) -> str | None:
    if not module or not module.startswith(PREFIX):
        return None
    rest = module[len(PREFIX) :]
    return rest.split(".", 1)[0] if rest else None


def source_component(path: Path, components_root: Path) -> str:
    return path.relative_to(components_root).parts[0]


def imports_for_file(path: Path) -> set[str]:
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

    print("source\ttarget")
    for src in sorted(edges):
        for dst in sorted(edges[src]):
            if src != dst:
                print(f"{src}\t{dst}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
