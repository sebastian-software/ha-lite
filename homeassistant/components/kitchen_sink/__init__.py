"""The Kitchen Sink integration contains demonstrations of various odds and ends.

This sets up a demo environment of features which are obscure or which represent
incorrect behavior, and are thus not wanted in the demo integration.
"""

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import AnyDeviceEntry
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .services import async_setup_services

COMPONENTS_WITH_DEMO_PLATFORM = [
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.FAN,
    Platform.EVENT,
    Platform.IMAGE,
    Platform.INFRARED,
    Platform.LAWN_MOWER,
    Platform.LOCK,
    Platform.NOTIFY,
    Platform.RADIO_FREQUENCY,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.WEATHER,
]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the demo environment."""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data={}
        )
    )

    async_setup_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set the config entry up."""
    # Set up demo platforms with config entry
    await hass.config_entries.async_forward_entry_setups(
        entry, COMPONENTS_WITH_DEMO_PLATFORM
    )

    # Create issues
    _create_issues(hass)

    # Start a reauth flow
    entry.async_start_reauth(hass)

    # Reload config entry when subentries are added/removed/updated
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry on update (e.g. subentry added/removed)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry, COMPONENTS_WITH_DEMO_PLATFORM
    )


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: AnyDeviceEntry
) -> bool:
    """Remove a config entry from a device."""

    # Allow deleting any device except statistics_issues, just to give
    # something to test the negative case.
    for identifier in device_entry.identifiers:
        if identifier[0] == DOMAIN and identifier[1] == "statistics_issues":
            return False

    return True


def _create_issues(hass: HomeAssistant) -> None:
    """Create some issue registry issues."""
    async_create_issue(
        hass,
        DOMAIN,
        "transmogrifier_deprecated",
        breaks_in_ha_version="2023.1.1",
        is_fixable=False,
        learn_more_url="https://en.wiktionary.org/wiki/transmogrifier",
        severity=IssueSeverity.WARNING,
        translation_key="transmogrifier_deprecated",
    )

    async_create_issue(
        hass,
        DOMAIN,
        "out_of_blinker_fluid",
        breaks_in_ha_version="2023.1.1",
        is_fixable=True,
        learn_more_url="https://www.youtube.com/watch?v=b9rntRxLlbU",
        severity=IssueSeverity.CRITICAL,
        translation_key="out_of_blinker_fluid",
    )

    async_create_issue(
        hass,
        DOMAIN,
        "unfixable_problem",
        is_fixable=False,
        learn_more_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        severity=IssueSeverity.WARNING,
        translation_key="unfixable_problem",
    )

    async_create_issue(
        hass,
        DOMAIN,
        "bad_psu",
        is_fixable=True,
        learn_more_url="https://www.youtube.com/watch?v=b9rntRxLlbU",
        severity=IssueSeverity.CRITICAL,
        translation_key="bad_psu",
    )

    async_create_issue(
        hass,
        DOMAIN,
        "cold_tea",
        is_fixable=True,
        severity=IssueSeverity.WARNING,
        translation_key="cold_tea",
    )
