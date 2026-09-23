"""Everything bootstrap sets up by name is in the retained closure.

The closure tool follows imports and manifests. Bootstrap and the generated
configuration.yaml name integrations as strings, which it cannot see, so a
deletion wave could remove one of them without a finding, and a fresh
installation or recovery mode would fail to set it up.
"""

import json
from pathlib import Path
import re

import pytest

from homeassistant import bootstrap, config

CLOSURE = frozenset(
    json.loads(
        (
            Path(__file__).parents[2] / "docs/architecture/retained-closure.json"
        ).read_text(encoding="utf-8")
    )["closure"]
)


@pytest.mark.parametrize(
    "domains",
    [
        pytest.param(bootstrap.CORE_INTEGRATIONS, id="core"),
        pytest.param(
            {
                domain
                for _, stage, _ in bootstrap.STAGE_0_INTEGRATIONS
                for domain in stage
            },
            id="stage 0",
        ),
        pytest.param(bootstrap.STAGE_1_INTEGRATIONS, id="stage 1"),
        pytest.param(bootstrap.DEFAULT_INTEGRATIONS, id="defaults"),
        pytest.param(bootstrap.DEFAULT_INTEGRATIONS_RECOVERY_MODE, id="recovery"),
        pytest.param(bootstrap.CRITICAL_INTEGRATIONS, id="critical"),
        pytest.param(
            set(re.findall(r"^(\w+):", config.DEFAULT_CONFIG, re.MULTILINE)),
            id="configuration.yaml",
        ),
    ],
)
def test_bootstrap_names_only_retained_domains(domains: set[str]) -> None:
    """Each domain bootstrap sets up by name survives deletion."""
    assert set(domains) - CLOSURE == set()
