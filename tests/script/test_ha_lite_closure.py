"""Tests for the retained dependency closure tool.

The tool gates CI, so the behaviours that make the gate trustworthy are pinned
here: what counts as a domain, which edges grow the closure, what is reported
as a finding, and which capabilities are flagged without growing the closure.
"""

import json
from pathlib import Path

import pytest

from script import ha_lite_closure


def write_component(
    components: Path,
    domain: str,
    *,
    manifest: dict | None = None,
    files: dict[str, str] | None = None,
) -> None:
    """Create one component directory with a manifest and optional modules."""
    directory = components / domain
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(
        json.dumps({"domain": domain, **(manifest or {})}), encoding="utf-8"
    )
    for name, source in (files or {}).items():
        (directory / name).write_text(source, encoding="utf-8")


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the tool at a synthetic component tree and config."""
    components = tmp_path / "homeassistant" / "components"
    components.mkdir(parents=True)
    monkeypatch.setattr(ha_lite_closure, "ROOT", tmp_path)
    monkeypatch.setattr(ha_lite_closure, "COMPONENTS", components)
    monkeypatch.setattr(ha_lite_closure, "CONFIG", tmp_path / "config.json")
    return components


def write_config(
    tmp_path: Path,
    *,
    roots: list[str],
    accepted: dict[str, dict] | None = None,
    platforms: list[str] | None = None,
) -> None:
    """Write the checked-in-style config the tool reads."""
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "roots": {"test": roots},
                "cross_cutting_platforms": platforms or [],
                "accepted_transitive": accepted or {},
            }
        ),
        encoding="utf-8",
    )


def test_only_manifest_directories_are_domains(tree: Path, tmp_path: Path) -> None:
    """Build output under components/ is not an integration.

    A working checkout carries __pycache__ and a fresh clone does not, which
    previously made the generated closure irreproducible.
    """
    write_component(tree, "alpha")
    (tree / "__pycache__").mkdir()
    (tree / "__pycache__" / "alpha.pyc").write_bytes(b"\x00")

    write_config(tmp_path, roots=["alpha"])
    result = ha_lite_closure.analyze()

    assert result["domains"] == {"alpha"}


def test_hard_edges_grow_the_closure(tree: Path, tmp_path: Path) -> None:
    """A module-level import and a manifest dependency both pull a domain in."""
    write_component(
        tree,
        "alpha",
        manifest={"dependencies": ["beta"]},
        files={
            "__init__.py": "from homeassistant.components.gamma import DOMAIN\n",
        },
    )
    write_component(tree, "beta")
    write_component(tree, "gamma")

    write_config(tmp_path, roots=["alpha"], accepted={})
    result = ha_lite_closure.analyze()

    assert result["closure"] == {"alpha", "beta", "gamma"}


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        pytest.param(
            "def setup():\n    from homeassistant.components.beta import DOMAIN\n",
            "import_deferred",
            id="function-local",
        ),
        pytest.param(
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from homeassistant.components.beta import DOMAIN\n",
            "import_typing",
            id="type-checking",
        ),
    ],
)
def test_soft_imports_stay_out_of_the_closure(
    tree: Path, tmp_path: Path, source: str, kind: str
) -> None:
    """Deferred and TYPE_CHECKING imports are reported, not retained."""
    write_component(tree, "alpha", files={"__init__.py": source})
    write_component(tree, "beta")

    write_config(tmp_path, roots=["alpha"])
    result = ha_lite_closure.analyze()

    assert result["closure"] == {"alpha"}
    assert [(e.target, e.kind) for e in result["latent"]] == [("beta", kind)]


def test_after_dependencies_stay_out_of_the_closure(tree: Path, tmp_path: Path) -> None:
    """An ordering hint is not a requirement."""
    write_component(tree, "alpha", manifest={"after_dependencies": ["beta"]})
    write_component(tree, "beta")

    write_config(tmp_path, roots=["alpha"])
    result = ha_lite_closure.analyze()

    assert result["closure"] == {"alpha"}


def test_unreviewed_closure_member_is_a_finding(tree: Path, tmp_path: Path) -> None:
    """Coupling into a domain with no reviewed entry fails the gate."""
    write_component(tree, "alpha", manifest={"dependencies": ["beta"]})
    write_component(tree, "beta")

    write_config(tmp_path, roots=["alpha"])
    result = ha_lite_closure.analyze()

    assert result["unreviewed"] == ["beta"]
    assert result["reason"]["beta"].source == "alpha"


def test_stale_accepted_entry_is_a_finding(tree: Path, tmp_path: Path) -> None:
    """An entry that is no longer reachable keeps the config from rotting."""
    write_component(tree, "alpha")

    write_config(
        tmp_path,
        roots=["alpha"],
        accepted={"beta": {"status": "retained", "reason": "gone", "issue": None}},
    )
    result = ha_lite_closure.analyze()

    assert result["stale_accepted"] == ["beta"]


def test_missing_root_is_a_finding(tree: Path, tmp_path: Path) -> None:
    """A declared root that is absent from the tree is reported."""
    write_component(tree, "alpha")

    write_config(tmp_path, roots=["alpha", "ghost"])
    result = ha_lite_closure.analyze()

    assert result["missing_roots"] == ["ghost"]


def test_platform_provider_is_flagged_without_growing_the_closure(
    tree: Path, tmp_path: Path
) -> None:
    """Runtime-resolved platforms are a capability warning, not a dependency.

    `beta` provides a trigger platform that the runtime loads by name. Nothing
    imports it, so it must stay outside the closure, but deleting it would drop
    the capability silently -- which is why it is reported.
    """
    write_component(tree, "alpha")
    write_component(
        tree,
        "beta",
        manifest={"integration_type": "system"},
        files={"trigger.py": "TRIGGERS = {}\n"},
    )

    write_config(tmp_path, roots=["alpha"], platforms=["trigger"])
    result = ha_lite_closure.analyze()

    assert result["closure"] == {"alpha"}
    assert result["capability_at_risk"] == {
        "beta": {"integration_type": "system", "platforms": ["trigger"]}
    }


def test_platform_provider_inside_the_closure_is_not_flagged(
    tree: Path, tmp_path: Path
) -> None:
    """A retained provider is not at risk; only deletable ones are reported."""
    write_component(
        tree,
        "alpha",
        manifest={"integration_type": "system"},
        files={"trigger.py": "TRIGGERS = {}\n"},
    )

    write_config(tmp_path, roots=["alpha"], platforms=["trigger"])
    result = ha_lite_closure.analyze()

    assert result["capability_at_risk"] == {}
