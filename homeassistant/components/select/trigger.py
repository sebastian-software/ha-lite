"""Provides triggers for selects."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.trigger import (
    ENTITY_STATE_TRIGGER_SCHEMA,
    EntityTriggerBase,
    Trigger,
)

from .const import DOMAIN

SELECT_DOMAIN_SPECS: dict[str, DomainSpec] = {
    DOMAIN: DomainSpec(),
}


class SelectionChangedTrigger(EntityTriggerBase):
    """Trigger for select entity when its selection changes."""

    _domain_specs = SELECT_DOMAIN_SPECS
    _schema = ENTITY_STATE_TRIGGER_SCHEMA


TRIGGERS: dict[str, type[Trigger]] = {
    "selection_changed": SelectionChangedTrigger,
}


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:
    """Return the triggers for selects."""
    return TRIGGERS
