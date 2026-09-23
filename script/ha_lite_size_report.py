#!/usr/bin/env python3
"""Report reproducible ha-lite source-size metrics from tracked files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Metric:
    """Accumulated file count, line count and byte size for one metric row."""

    files: int = 0
    lines: int = 0
    bytes: int = 0

    def add(self, path: Path) -> None:
        """Fold one file's size into this metric."""
        data = path.read_bytes()
        self.files += 1
        self.bytes += len(data)
        self.lines += data.count(b"\n") + (bool(data) and not data.endswith(b"\n"))


def tracked_files() -> list[Path]:
    """Return tracked files in the current checkout."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        ROOT / item.decode()
        for item in result.stdout.split(b"\0")
        if item and (ROOT / item.decode()).is_file()
    ]


def fmt_bytes(value: int) -> str:
    """Format bytes using decimal units for easy comparison with repository sizes."""
    if value < 1000:
        return f"{value} B"
    if value < 1_000_000:
        return f"{value / 1000:.1f} KB"
    return f"{value / 1_000_000:.2f} MB"


def main() -> int:
    """Print Markdown metrics suitable for copying into the README."""
    files = tracked_files()

    groups: dict[str, Metric] = {
        "Tracked files in repository": Metric(),
        "Tracked Python files": Metric(),
        "Product Python under `homeassistant/`": Metric(),
        "Python under `homeassistant/components/`": Metric(),
        "Core `frontend/` + `lovelace/` Python": Metric(),
        "Python tests under `tests/`": Metric(),
    }

    component_domains: set[str] = set()

    for path in files:
        rel = path.relative_to(ROOT)
        rel_str = rel.as_posix()
        groups["Tracked files in repository"].add(path)

        if not rel_str.endswith(".py"):
            continue

        groups["Tracked Python files"].add(path)

        if rel_str.startswith("homeassistant/"):
            groups["Product Python under `homeassistant/`"].add(path)

        if rel_str.startswith("homeassistant/components/"):
            groups["Python under `homeassistant/components/`"].add(path)
            parts = rel.parts
            # Modules directly under components/, such as the script domain
            # marker, are not domains.
            if len(parts) >= 4:
                component_domains.add(parts[2])

        if rel_str.startswith(
            ("homeassistant/components/frontend/", "homeassistant/components/lovelace/")
        ):
            groups["Core `frontend/` + `lovelace/` Python"].add(path)

        if rel_str.startswith("tests/"):
            groups["Python tests under `tests/`"].add(path)

    print("| Metric | Files | Lines | Bytes |")
    print("| --- | ---: | ---: | ---: |")
    for name, metric in groups.items():
        print(
            f"| {name} | {metric.files:,} | {metric.lines:,} | {fmt_bytes(metric.bytes)} |"
        )
    print(f"| Top-level component domains | {len(component_domains):,} | — | — |")

    return 0


if __name__ == "__main__":
    sys.exit(main())
