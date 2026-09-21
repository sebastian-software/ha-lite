#!/usr/bin/env python3
"""Check that trigger and condition targets agree with their Python filters.

A trigger declares which entities it applies to twice:

- `trigger.py` sets `_domain_specs`, which is what actually filters at runtime;
- `triggers.yaml` sets `target.entity`, which is what `websocket_api` reports
  through `triggers/target` when something asks what it may act on.

Conditions do the same through `condition.py` and `conditions.yaml`.

Nothing upstream compares the two. `script/hassfest/triggers.py` validates the
YAML against a schema and checks that strings exist, but never imports the
Python module. So the two can drift, and when they do nothing fails: the
trigger keeps firing on what `_domain_specs` says, while capability discovery
advertises something else.

That is not hypothetical. Removing the `input_*` helpers cleaned up the Python
filters and left four deleted domains in seven YAML targets, which this check
found.

ADR 0011 says a runtime-resolved platform is a capability rather than a
dependency, and ADR 0012 keeps the device-class providers because that
capability is what an external decision engine reads. A wrong target makes that
answer wrong, so it is worth a build failure.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml

from homeassistant.helpers.automation import ANY_DEVICE_CLASS

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "homeassistant" / "components"

# (platform module, table attribute, description file)
PLATFORMS = (
    ("trigger", "TRIGGERS", "triggers.yaml"),
    ("condition", "CONDITIONS", "conditions.yaml"),
)


@dataclass(frozen=True)
class Finding:
    """One entry whose YAML target and Python filters disagree."""

    domain: str
    platform: str
    name: str
    yaml_targets: tuple[tuple[str | None, str | None], ...]
    python_targets: tuple[tuple[str | None, str | None], ...]

    @property
    def missing_domains(self) -> tuple[str, ...]:
        """Return domains the YAML advertises that no longer exist in the tree."""
        advertised = {domain for domain, _ in self.yaml_targets if domain}
        return tuple(sorted(d for d in advertised if not (COMPONENTS / d).is_dir()))


def _normalize_device_class(value: Any) -> str | None:
    """Return a comparable device class, or None when any class matches.

    `DomainSpec` defaults to the ANY_DEVICE_CLASS sentinel, which an entity
    filter expresses by leaving `device_class` out entirely.
    """
    if value is None or value is ANY_DEVICE_CLASS:
        return None
    return str(getattr(value, "value", value))


def _as_list(value: Any) -> list[Any]:
    """Return a list for a field the schema allows as scalar or list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def yaml_targets(spec: dict[str, Any]) -> set[tuple[str | None, str | None]]:
    """Return the (domain, device_class) pairs an entry advertises."""
    pairs: set[tuple[str | None, str | None]] = set()
    for entity_filter in _as_list((spec.get("target") or {}).get("entity")):
        domains = _as_list(entity_filter.get("domain")) or [None]
        device_classes = _as_list(entity_filter.get("device_class")) or [None]
        for domain in domains:
            for device_class in device_classes:
                pairs.add((domain, _normalize_device_class(device_class)))
    return pairs


def python_targets(cls: type) -> set[tuple[str | None, str | None]] | None:
    """Return the pairs a trigger or condition filters on, or None.

    None means the class does not filter by entity at all, so there is nothing
    to compare against.
    """
    specs = getattr(cls, "_domain_specs", None)
    if not specs:
        return None
    return {
        (domain, _normalize_device_class(getattr(spec, "device_class", None)))
        for domain, spec in specs.items()
    }


def analyze() -> dict[str, Any]:
    """Compare every entry that declares its targets in both places."""
    findings: list[Finding] = []
    entries = compared = 0

    for platform, attribute, filename in PLATFORMS:
        for module_path in sorted(COMPONENTS.glob(f"*/{platform}.py")):
            domain = module_path.parent.name
            descriptions = module_path.parent / filename
            if not descriptions.is_file():
                continue

            module = importlib.import_module(
                f"homeassistant.components.{domain}.{platform}"
            )
            table = getattr(module, attribute, None)
            if table is None:
                # The table is built at runtime, so there is nothing static to
                # compare. MQTT does this.
                continue

            data = yaml.safe_load(descriptions.read_text(encoding="utf-8")) or {}

            for name, cls in table.items():
                entries += 1
                expected = python_targets(cls)
                spec = data.get(name)
                if (
                    expected is None
                    or not isinstance(spec, dict)
                    or spec.get("target") is None
                ):
                    continue

                compared += 1
                advertised = yaml_targets(spec)
                if advertised != expected:
                    findings.append(
                        Finding(
                            domain=domain,
                            platform=platform,
                            name=name,
                            yaml_targets=tuple(sorted(advertised, key=str)),
                            python_targets=tuple(sorted(expected, key=str)),
                        )
                    )

    return {"entries": entries, "compared": compared, "findings": findings}


def format_report(result: dict[str, Any]) -> str:
    """Render the human-readable report."""
    findings: list[Finding] = result["findings"]
    lines = [
        "# ha-lite trigger and condition target consistency",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Entries declared in Python | {result['entries']:,} |",
        f"| Comparable against a YAML target | {result['compared']:,} |",
        f"| Disagreeing | {len(findings):,} |",
        "",
    ]

    if not findings:
        lines.append("Every advertised target matches what the entry filters on.")
        return "\n".join(lines)

    lines += [
        "## Findings",
        "",
        "`websocket_api` answers `triggers/target` and `conditions/target` from",
        "the YAML, while the runtime filters on the Python specs. Where they",
        "disagree, capability discovery is wrong.",
        "",
        "| Entry | Advertised | Filters on | Deleted domains |",
        "| --- | --- | --- | --- |",
    ]
    for finding in findings:
        advertised = ", ".join(f"`{d}`" for d, _ in finding.yaml_targets) or "—"
        filters = ", ".join(f"`{d}`" for d, _ in finding.python_targets) or "—"
        gone = ", ".join(f"`{d}`" for d in finding.missing_domains) or "—"
        lines.append(
            f"| `{finding.domain}.{finding.name}` | {advertised} | {filters} | {gone} |"
        )

    return "\n".join(lines)


def as_json(result: dict[str, Any]) -> dict[str, Any]:
    """Render a machine-readable result."""
    return {
        "entries": result["entries"],
        "compared": result["compared"],
        "findings": [
            {
                "domain": f.domain,
                "platform": f.platform,
                "name": f.name,
                "advertised": [list(pair) for pair in f.yaml_targets],
                "filters_on": [list(pair) for pair in f.python_targets],
                "deleted_domains": list(f.missing_domains),
            }
            for f in result["findings"]
        ],
    }


def main() -> int:
    """Run the check."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when an advertised target disagrees",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the machine-readable result"
    )
    args = parser.parse_args()

    result = analyze()

    if args.json:
        print(json.dumps(as_json(result), indent=2))
    else:
        print(format_report(result))

    if args.check and result["findings"]:
        print(
            f"\n::error::{len(result['findings'])} trigger or condition entries "
            "advertise targets they do not filter on.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
