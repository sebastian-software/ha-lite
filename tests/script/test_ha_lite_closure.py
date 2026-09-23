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
    excluded: list[str] | None = None,
) -> None:
    """Write the checked-in-style config the tool reads."""
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "roots": {"test": roots},
                "cross_cutting_platforms": platforms or [],
                "accepted_transitive": accepted or {},
                "excluded": {"test": excluded or []},
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


def test_package_level_import_names_the_domain(tree: Path, tmp_path: Path) -> None:
    """`from homeassistant.components import beta` binds just as hard.

    The domain is in the import list rather than the module path, and reading
    only the module path missed 602 such imports across 495 files -- including
    onboarding's hard import of person, which made person look deletable.
    """
    write_component(
        tree,
        "alpha",
        files={"__init__.py": "from homeassistant.components import beta\n"},
    )
    write_component(tree, "beta")

    write_config(tmp_path, roots=["alpha"], accepted={})
    result = ha_lite_closure.analyze()

    assert result["closure"] == {"alpha", "beta"}


def test_package_level_import_in_a_function_stays_soft(
    tree: Path, tmp_path: Path
) -> None:
    """Naming the domain in the import list does not change how it binds."""
    write_component(
        tree,
        "alpha",
        files={
            "__init__.py": (
                "def setup():\n    from homeassistant.components import beta\n"
            )
        },
    )
    write_component(tree, "beta")

    write_config(tmp_path, roots=["alpha"])
    result = ha_lite_closure.analyze()

    assert result["closure"] == {"alpha"}
    assert [(e.target, e.kind) for e in result["latent"]] == [
        ("beta", "import_deferred")
    ]


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


def test_component_outside_the_closure_is_catalog(tree: Path, tmp_path: Path) -> None:
    """A component no root reaches belongs to the catalog, which is no finding."""
    write_component(tree, "alpha")
    write_component(tree, "catalogued")

    write_config(tmp_path, roots=["alpha"])
    result = ha_lite_closure.analyze()

    assert result["catalog"] == ["catalogued"]
    assert ha_lite_closure.as_json(result)["catalog"] == ["catalogued"]
    assert not any(ha_lite_closure.as_json(result)["findings"].values())


def test_excluded_product_layer_in_the_tree_is_a_finding(
    tree: Path, tmp_path: Path
) -> None:
    """A removed product layer that comes back fails the gate."""
    write_component(tree, "alpha")
    write_component(tree, "frontend")

    write_config(tmp_path, roots=["alpha"], excluded=["frontend", "recorder"])
    result = ha_lite_closure.analyze()

    assert result["excluded_in_tree"] == ["frontend"]
    assert ha_lite_closure.as_json(result)["findings"]["excluded_in_tree"] == [
        "frontend"
    ]


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


def write_core(tmp_path: Path, name: str, source: str) -> None:
    """Create a core module outside homeassistant/components."""
    path = tmp_path / "homeassistant" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "source"),
    [
        pytest.param(
            "bootstrap.py",
            "from .components import beta\n",
            id="package-level",
        ),
        pytest.param(
            "bootstrap.py",
            "from .components.beta import DOMAIN\n",
            id="module-level",
        ),
        pytest.param(
            "helpers/setup.py",
            "from ..components import beta\n",
            id="two-levels-up",
        ),
    ],
)
def test_relative_import_in_core_binds(
    tree: Path, tmp_path: Path, name: str, source: str
) -> None:
    """A relative import from core is as hard as its absolute spelling.

    bootstrap.py pre-imports its components as `from .components import ...`.
    Skipping relative imports hid that default_config, and through its manifest
    the whole voice stack, was part of what the runtime loads.
    """
    write_core(tmp_path, name, source)
    write_component(tree, "beta")

    write_config(tmp_path, roots=[], accepted={})
    result = ha_lite_closure.analyze()

    assert result["closure"] == {"beta"}
    assert result["reason"]["beta"].source == ha_lite_closure.CORE


def test_relative_import_inside_a_component_stays_inside(
    tree: Path, tmp_path: Path
) -> None:
    """`from .const import DOMAIN` resolves to the component itself."""
    write_component(
        tree,
        "alpha",
        files={"__init__.py": "from .const import DOMAIN\nfrom . import const\n"},
    )

    write_config(tmp_path, roots=["alpha"])
    result = ha_lite_closure.analyze()

    assert result["closure"] == {"alpha"}
    assert not [edge for edge in result["edges"] if edge.source == "alpha"]


def test_core_soft_edge_is_latent_coupling(tree: Path, tmp_path: Path) -> None:
    """Core is not a closure member, but its deferred imports are still reported.

    helpers/service.py imports five entity domains inside a function. Leaving
    core out of the latent report hid that the call breaks once they are gone.
    """
    write_core(
        tmp_path,
        "helpers/service.py",
        "def load():\n    from homeassistant.components import beta\n",
    )
    write_component(tree, "beta")

    write_config(tmp_path, roots=[])
    result = ha_lite_closure.analyze()

    assert result["closure"] == set()
    assert [(e.source, e.target, e.kind) for e in result["latent"]] == [
        (ha_lite_closure.CORE, "beta", "import_deferred")
    ]


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("from homeassistant.components.gone import X\n", id="runtime"),
        pytest.param(
            "def load():\n    from ..components.gone import X\n", id="deferred"
        ),
        pytest.param(
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from homeassistant.components.gone import X\n",
            id="typing",
        ),
    ],
)
def test_retained_import_of_a_missing_component_is_a_finding(
    tree: Path, tmp_path: Path, source: str
) -> None:
    """Retained code naming a deleted component fails the gate, however soft.

    core_config.py kept a deferred import of the deleted frontend inside a
    storage migration; it only failed when an old store was migrated.
    """
    write_core(tmp_path, "helpers/thing.py", source)

    write_config(tmp_path, roots=[])
    result = ha_lite_closure.analyze()

    assert [(e.target, e.via) for e in result["dangling"]] == [
        ("gone", "homeassistant/helpers/thing.py")
    ]


def test_catalog_import_of_a_missing_component_is_a_finding(
    tree: Path, tmp_path: Path
) -> None:
    """A catalog member that needs a removed component cannot load, so it fails.

    This is what keeps an integration that still imports a removed product
    layer out of the tree until it is decoupled.
    """
    write_component(
        tree,
        "catalogued",
        files={"__init__.py": "from homeassistant.components.gone import X\n"},
    )
    write_component(tree, "alpha")

    write_config(tmp_path, roots=["alpha"])
    result = ha_lite_closure.analyze()

    assert [(e.source, e.target) for e in result["dangling"]] == [
        ("catalogued", "gone")
    ]


def test_after_dependency_on_a_missing_component_is_not_a_finding(
    tree: Path, tmp_path: Path
) -> None:
    """The loader ignores an ordering hint on a domain that is not there."""
    write_component(tree, "alpha", manifest={"after_dependencies": ["gone"]})

    write_config(tmp_path, roots=["alpha"])
    result = ha_lite_closure.analyze()

    assert result["dangling"] == []
