"""Tests for the trigger and condition target consistency check.

The check gates CI, so the behaviours that make it trustworthy are pinned here:
which entries it compares, which it leaves alone, and that a drift between the
YAML target and the Python filter is reported rather than tolerated.
"""

from pathlib import Path
import sys
import types
from typing import Any

import pytest
import yaml

from homeassistant.helpers.automation import ANY_DEVICE_CLASS, DomainSpec
from script import ha_lite_trigger_targets


def make_entry(specs: dict[str, DomainSpec] | None) -> type:
    """Build a trigger-like class carrying the given domain specs."""
    return type("_Trigger", (), {"_domain_specs": specs})


@pytest.fixture
def components(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the check at a synthetic component tree."""
    root = tmp_path / "homeassistant" / "components"
    root.mkdir(parents=True)
    monkeypatch.setattr(ha_lite_trigger_targets, "COMPONENTS", root)
    return root


def write_platform(
    components: Path,
    domain: str,
    *,
    platform: str = "trigger",
    table: dict[str, type],
    descriptions: dict[str, Any] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create one component's description file and stub its Python module."""
    directory = components / domain
    directory.mkdir(parents=True, exist_ok=True)

    if descriptions is not None:
        filename = "triggers.yaml" if platform == "trigger" else "conditions.yaml"
        (directory / filename).write_text(
            yaml.safe_dump(descriptions), encoding="utf-8"
        )

    module = types.ModuleType(f"homeassistant.components.{domain}.{platform}")
    setattr(module, "TRIGGERS" if platform == "trigger" else "CONDITIONS", table)
    monkeypatch.setitem(
        sys.modules, f"homeassistant.components.{domain}.{platform}", module
    )
    # The check discovers components by the presence of the platform module.
    (directory / f"{platform}.py").write_text("", encoding="utf-8")


def test_matching_target_is_not_a_finding(
    components: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An entry whose advertised target matches its filter passes."""
    write_platform(
        components,
        "motion",
        table={
            "detected": make_entry({"binary_sensor": DomainSpec(device_class="motion")})
        },
        descriptions={
            "detected": {
                "target": {
                    "entity": [{"domain": "binary_sensor", "device_class": "motion"}]
                }
            }
        },
        monkeypatch=monkeypatch,
    )

    result = ha_lite_trigger_targets.analyze()

    assert result["compared"] == 1
    assert result["findings"] == []


def test_drifting_target_is_a_finding(
    components: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Advertising a domain the entry does not filter on is reported.

    This is the shape the removed `input_*` helpers left behind: the Python
    filter was cleaned up and the YAML target was not.
    """
    write_platform(
        components,
        "switch",
        table={"turned_on": make_entry({"switch": DomainSpec()})},
        descriptions={
            "turned_on": {
                "target": {
                    "entity": [{"domain": "switch"}, {"domain": "input_boolean"}]
                }
            }
        },
        monkeypatch=monkeypatch,
    )

    result = ha_lite_trigger_targets.analyze()

    assert len(result["findings"]) == 1
    finding = result["findings"][0]
    assert finding.name == "turned_on"
    assert ("input_boolean", None) in finding.yaml_targets
    assert ("input_boolean", None) not in finding.python_targets


def test_finding_names_domains_absent_from_the_tree(
    components: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A target pointing at a deleted component is called out as such."""
    write_platform(
        components,
        "switch",
        table={"turned_on": make_entry({"switch": DomainSpec()})},
        descriptions={
            "turned_on": {
                "target": {
                    "entity": [{"domain": "switch"}, {"domain": "input_boolean"}]
                }
            }
        },
        monkeypatch=monkeypatch,
    )
    (components / "switch").mkdir(exist_ok=True)

    result = ha_lite_trigger_targets.analyze()

    assert result["findings"][0].missing_domains == ("input_boolean",)


def test_any_device_class_matches_an_omitted_key(
    components: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ANY_DEVICE_CLASS default is how a filter says 'no device class'.

    An entity filter expresses the same thing by leaving the key out, so the
    two must compare equal or every unfiltered entry would be a false finding.
    """
    write_platform(
        components,
        "switch",
        table={
            "turned_on": make_entry(
                {"switch": DomainSpec(device_class=ANY_DEVICE_CLASS)}
            )
        },
        descriptions={"turned_on": {"target": {"entity": [{"domain": "switch"}]}}},
        monkeypatch=monkeypatch,
    )

    result = ha_lite_trigger_targets.analyze()

    assert result["findings"] == []


def test_scalar_and_list_filters_compare_equal(
    components: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The schema allows `domain` as a scalar or a list; both are the same."""
    write_platform(
        components,
        "text",
        table={"changed": make_entry({"text": DomainSpec()})},
        descriptions={"changed": {"target": {"entity": {"domain": ["text"]}}}},
        monkeypatch=monkeypatch,
    )

    result = ha_lite_trigger_targets.analyze()

    assert result["compared"] == 1
    assert result["findings"] == []


def test_entry_without_entity_filters_is_not_compared(
    components: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A trigger that does not filter by entity has nothing to check."""
    write_platform(
        components,
        "moon",
        table={"phase_changed": make_entry(None)},
        descriptions={"phase_changed": {"target": {"entity": [{"domain": "sensor"}]}}},
        monkeypatch=monkeypatch,
    )

    result = ha_lite_trigger_targets.analyze()

    assert result["entries"] == 1
    assert result["compared"] == 0
    assert result["findings"] == []


def test_entry_without_a_yaml_target_is_not_compared(
    components: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An entry that advertises no target makes no claim to contradict."""
    write_platform(
        components,
        "moon",
        table={"phase_changed": make_entry({"sensor": DomainSpec()})},
        descriptions={"phase_changed": {"fields": {}}},
        monkeypatch=monkeypatch,
    )

    result = ha_lite_trigger_targets.analyze()

    assert result["entries"] == 1
    assert result["compared"] == 0


def test_runtime_built_table_is_skipped(
    components: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A platform that builds its table at runtime has nothing static to read.

    MQTT is the real case: it has no module-level TRIGGERS.
    """
    directory = components / "mqtt"
    directory.mkdir()
    (directory / "trigger.py").write_text("", encoding="utf-8")
    (directory / "triggers.yaml").write_text("{}\n", encoding="utf-8")
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.components.mqtt.trigger",
        types.ModuleType("homeassistant.components.mqtt.trigger"),
    )

    result = ha_lite_trigger_targets.analyze()

    assert result["entries"] == 0
    assert result["findings"] == []
