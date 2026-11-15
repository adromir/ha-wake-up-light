"""Wake Up Light custom component for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DEFAULT_SNOOZE_MINUTES,
    DOMAIN,
    PLATFORMS,
)
from .simulator import WakeUpLightCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_START = "start"
SERVICE_STOP = "stop"
SERVICE_SNOOZE = "snooze"

SERVICE_START_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)

SERVICE_STOP_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
        vol.Optional("turn_off", default=False): cv.boolean,
    }
)

SERVICE_SNOOZE_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
        vol.Optional("minutes", default=DEFAULT_SNOOZE_MINUTES): cv.positive_int,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Wake Up Light from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    config_data = {**entry.data, **entry.options}
    coordinator = WakeUpLightCoordinator(hass, entry.entry_id, config_data)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Initial schedule calculation
    coordinator.reschedule()

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Register domain services if not already registered
    _register_services(hass)

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator: WakeUpLightCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        config_data = {**entry.data, **entry.options}
        coordinator.update_options(config_data)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: WakeUpLightCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        coordinator.async_stop_simulation(turn_off_lights=False)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    """Register custom services for Wake Up Light."""
    if hass.services.has(DOMAIN, SERVICE_START):
        return

    async def _handle_start(call: ServiceCall) -> None:
        target_entry_id = call.data.get("entry_id")
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            if target_entry_id is None or entry_id == target_entry_id:
                coordinator.async_start_simulation()

    async def _handle_stop(call: ServiceCall) -> None:
        target_entry_id = call.data.get("entry_id")
        turn_off = call.data.get("turn_off", False)
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            if target_entry_id is None or entry_id == target_entry_id:
                coordinator.async_stop_simulation(turn_off_lights=turn_off)

    async def _handle_snooze(call: ServiceCall) -> None:
        target_entry_id = call.data.get("entry_id")
        minutes = call.data.get("minutes", DEFAULT_SNOOZE_MINUTES)
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            if target_entry_id is None or entry_id == target_entry_id:
                coordinator.async_snooze(minutes=minutes)

    hass.services.async_register(
        DOMAIN, SERVICE_START, _handle_start, schema=SERVICE_START_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP, _handle_stop, schema=SERVICE_STOP_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SNOOZE, _handle_snooze, schema=SERVICE_SNOOZE_SCHEMA
    )
