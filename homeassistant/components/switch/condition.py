"""Provides conditions for switches."""

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.condition import Condition, make_entity_state_condition

from .const import DOMAIN

SWITCH_DOMAIN_SPECS: dict[str, DomainSpec] = {
    DOMAIN: DomainSpec(),
}

CONDITIONS: dict[str, type[Condition]] = {
    "is_off": make_entity_state_condition(SWITCH_DOMAIN_SPECS, STATE_OFF),
    "is_on": make_entity_state_condition(SWITCH_DOMAIN_SPECS, STATE_ON),
}


async def async_get_conditions(hass: HomeAssistant) -> dict[str, type[Condition]]:
    """Return the switch conditions."""
    return CONDITIONS
