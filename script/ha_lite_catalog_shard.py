#!/usr/bin/env python3
"""Print the catalog test directories one CI shard runs.

The catalog is every component outside the retained closure (see
`script/ha_lite_closure.py`). Its suites are too large for one job, so the CI
catalog job runs them in shards. Directories are weighed by the size of their
test modules and handed out greedily, heaviest first, to the lightest shard,
which keeps the shards close in running time without a test-count cache.

    python3 script/ha_lite_catalog_shard.py 3 10   # shard 3 of 10, 1-based
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from script import ha_lite_closure


def catalog_test_dirs() -> list[Path]:
    """Return the test directory of every catalog member that has one."""
    tests = ha_lite_closure.ROOT / "tests" / "components"
    return [
        tests / domain
        for domain in ha_lite_closure.analyze()["catalog"]
        if (tests / domain).is_dir()
    ]


def weight(directory: Path) -> int:
    """Approximate a suite's running time by the size of its test modules."""
    return sum(path.stat().st_size for path in directory.rglob("test_*.py")) or 1


def shards(directories: list[Path], count: int) -> list[list[Path]]:
    """Split directories into `count` shards of similar total weight."""
    buckets: list[list[Path]] = [[] for _ in range(count)]
    totals = [0] * count
    for directory in sorted(directories, key=lambda d: (-weight(d), d.name)):
        lightest = totals.index(min(totals))
        buckets[lightest].append(directory)
        totals[lightest] += weight(directory)
    return [sorted(bucket) for bucket in buckets]


def main() -> int:
    """Print one shard's directories, relative to the repository root."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("shard", type=int, help="1-based shard number")
    parser.add_argument("count", type=int, help="total number of shards")
    args = parser.parse_args()
    if not 1 <= args.shard <= args.count:
        parser.error("shard must be between 1 and count")

    for directory in shards(catalog_test_dirs(), args.count)[args.shard - 1]:
        print(directory.relative_to(ha_lite_closure.ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
