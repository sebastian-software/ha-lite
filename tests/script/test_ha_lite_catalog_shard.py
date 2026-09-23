"""Tests for the catalog shard splitter."""

from pathlib import Path

import pytest

from script import ha_lite_catalog_shard


def make_suite(tests: Path, domain: str, size: int) -> Path:
    """Create a test directory whose test module has `size` bytes."""
    directory = tests / domain
    directory.mkdir(parents=True)
    (directory / "test_init.py").write_text("#" * size, encoding="utf-8")
    return directory


@pytest.mark.parametrize("count", [1, 2, 3, 7])
def test_every_directory_lands_in_exactly_one_shard(tmp_path: Path, count: int) -> None:
    """No catalog suite is skipped or run twice, whatever the shard count."""
    directories = [
        make_suite(tmp_path, f"domain_{index}", size)
        for index, size in enumerate([500, 40, 40, 300, 10, 10, 120])
    ]

    result = ha_lite_catalog_shard.shards(directories, count)

    assert len(result) == count
    assert sorted(path for shard in result for path in shard) == sorted(directories)


def test_heaviest_suites_are_spread_across_shards(tmp_path: Path) -> None:
    """Two large suites never share a shard while a lighter one is free."""
    big_a = make_suite(tmp_path, "big_a", 1000)
    big_b = make_suite(tmp_path, "big_b", 900)
    small = [make_suite(tmp_path, f"small_{index}", 100) for index in range(4)]

    first, second = ha_lite_catalog_shard.shards([big_a, big_b, *small], 2)

    assert (big_a in first) != (big_b in first)
    assert len(first) + len(second) == 6
