"""Test switch triggers."""

from typing import Any

import pytest

from homeassistant.components.switch import DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests.components.common import (
    TriggerStateDescription,
    assert_trigger_behavior_all,
    assert_trigger_behavior_each,
    assert_trigger_behavior_first,
    assert_trigger_options_supported,
    parametrize_target_entities,
    parametrize_trigger_states,
    target_entities,
)

TRIGGER_STATES = [
    *parametrize_trigger_states(
        trigger="switch.turned_off",
        target_states=[STATE_OFF],
        other_states=[STATE_ON],
    ),
    *parametrize_trigger_states(
        trigger="switch.turned_on",
        target_states=[STATE_ON],
        other_states=[STATE_OFF],
    ),
]


@pytest.fixture
async def target_switches(hass: HomeAssistant) -> dict[str, list[str]]:
    """Create multiple switch entities associated with different targets."""
    return await target_entities(hass, DOMAIN)


@pytest.mark.parametrize(
    ("trigger_key", "base_options", "supports_behavior", "supports_duration"),
    [
        ("switch.turned_off", {}, True, True),
        ("switch.turned_on", {}, True, True),
    ],
)
async def test_switch_trigger_options_validation(
    hass: HomeAssistant,
    trigger_key: str,
    base_options: dict[str, Any] | None,
    supports_behavior: bool,
    supports_duration: bool,
) -> None:
    """Test that switch triggers support the expected options."""
    await assert_trigger_options_supported(
        hass,
        trigger_key,
        base_options,
        supports_behavior=supports_behavior,
        supports_duration=supports_duration,
    )


# --- Switch domain tests ---


@pytest.mark.parametrize(
    ("trigger_target_config", "entity_id", "entities_in_target"),
    parametrize_target_entities(DOMAIN),
)
@pytest.mark.parametrize(
    ("trigger", "trigger_options", "states"),
    TRIGGER_STATES,
)
async def test_switch_state_trigger_behavior_each(
    hass: HomeAssistant,
    target_switches: dict[str, list[str]],
    trigger_target_config: dict,
    entity_id: str,
    entities_in_target: int,
    trigger: str,
    trigger_options: dict[str, Any],
    states: list[TriggerStateDescription],
) -> None:
    """Test switch trigger fires when any switch changes to a state."""
    await assert_trigger_behavior_each(
        hass,
        target_entities=target_switches,
        trigger_target_config=trigger_target_config,
        entity_id=entity_id,
        entities_in_target=entities_in_target,
        trigger=trigger,
        trigger_options=trigger_options,
        states=states,
    )


@pytest.mark.parametrize(
    ("trigger_target_config", "entity_id", "entities_in_target"),
    parametrize_target_entities(DOMAIN),
)
@pytest.mark.parametrize(
    ("trigger", "trigger_options", "states"),
    TRIGGER_STATES,
)
async def test_switch_state_trigger_behavior_first(
    hass: HomeAssistant,
    target_switches: dict[str, list[str]],
    trigger_target_config: dict,
    entity_id: str,
    entities_in_target: int,
    trigger: str,
    trigger_options: dict[str, Any],
    states: list[TriggerStateDescription],
) -> None:
    """Test switch trigger fires when the first switch changes state."""
    await assert_trigger_behavior_first(
        hass,
        target_entities=target_switches,
        trigger_target_config=trigger_target_config,
        entity_id=entity_id,
        entities_in_target=entities_in_target,
        trigger=trigger,
        trigger_options=trigger_options,
        states=states,
    )


@pytest.mark.parametrize(
    ("trigger_target_config", "entity_id", "entities_in_target"),
    parametrize_target_entities(DOMAIN),
)
@pytest.mark.parametrize(
    ("trigger", "trigger_options", "states"),
    TRIGGER_STATES,
)
async def test_switch_state_trigger_behavior_all(
    hass: HomeAssistant,
    target_switches: dict[str, list[str]],
    trigger_target_config: dict,
    entity_id: str,
    entities_in_target: int,
    trigger: str,
    trigger_options: dict[str, Any],
    states: list[TriggerStateDescription],
) -> None:
    """Test switch trigger fires when all switches have changed state."""
    await assert_trigger_behavior_all(
        hass,
        target_entities=target_switches,
        trigger_target_config=trigger_target_config,
        entity_id=entity_id,
        entities_in_target=entities_in_target,
        trigger=trigger,
        trigger_options=trigger_options,
        states=states,
    )


# --- Input boolean domain tests ---


# --- Cross-domain test ---
