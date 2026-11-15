"""Button platform for Wake Up Light."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .simulator import WakeUpLightCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Wake Up Light buttons."""
    coordinator: WakeUpLightCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WakeUpLightStartButton(coordinator, entry),
            WakeUpLightStopButton(coordinator, entry),
            WakeUpLightSnoozeButton(coordinator, entry),
        ]
    )


class WakeUpLightStartButton(ButtonEntity):
    """Button to manually trigger the sunrise simulation immediately."""

    _attr_has_entity_name = True
    _attr_translation_key = "start"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(
        self, coordinator: WakeUpLightCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_btn_start"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Adromir",
            model="Sunrise Gradient Engine",
        )

    async def async_press(self) -> None:
        """Press the button."""
        self.coordinator.async_start_simulation()


class WakeUpLightStopButton(ButtonEntity):
    """Button to stop the active sunrise simulation."""

    _attr_has_entity_name = True
    _attr_translation_key = "stop"
    _attr_icon = "mdi:stop-circle-outline"

    def __init__(
        self, coordinator: WakeUpLightCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_btn_stop"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Adromir",
            model="Sunrise Gradient Engine",
        )

    async def async_press(self) -> None:
        """Press the button."""
        self.coordinator.async_stop_simulation(turn_off_lights=False)


class WakeUpLightSnoozeButton(ButtonEntity):
    """Button to snooze the light simulation."""

    _attr_has_entity_name = True
    _attr_translation_key = "snooze"
    _attr_icon = "mdi:alarm-snooze"

    def __init__(
        self, coordinator: WakeUpLightCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_btn_snooze"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Adromir",
            model="Sunrise Gradient Engine",
        )

    async def async_press(self) -> None:
        """Press the button."""
        self.coordinator.async_snooze()
