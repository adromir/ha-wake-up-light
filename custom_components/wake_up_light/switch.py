"""Switch platform for Wake Up Light."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CURVE_STYLE, CONF_LIGHT_ENTITIES, DOMAIN
from .simulator import WakeUpLightCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Wake Up Light switch."""
    coordinator: WakeUpLightCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WakeUpLightSwitch(coordinator, entry)])


class WakeUpLightSwitch(SwitchEntity):
    """Switch representing the enabled state of the wake up light profile."""

    _attr_has_entity_name = True
    _attr_translation_key = "profile"
    _attr_icon = "mdi:weather-sunset-up"

    def __init__(
        self, coordinator: WakeUpLightCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Adromir",
            model="Sunrise Gradient Engine",
        )

    async def async_added_to_hass(self) -> None:
        """Register coordinator update callbacks."""
        self.async_on_remove(
            self.coordinator.register_listener(self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator state updates."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if profile is enabled."""
        return self.coordinator.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable wake up light profile."""
        self.coordinator.enabled = True
        self.coordinator.reschedule()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable wake up light profile."""
        self.coordinator.enabled = False
        self.coordinator.async_stop_simulation(turn_off_lights=False)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "status": self.coordinator.status,
            "progress": self.coordinator.progress,
            "next_alarm": (
                self.coordinator.next_alarm.isoformat()
                if self.coordinator.next_alarm
                else None
            ),
            "next_start_time": (
                self.coordinator.next_start_time.isoformat()
                if self.coordinator.next_start_time
                else None
            ),
            "duration_minutes": self.coordinator.get_duration_minutes(),
            "curve_style": self.coordinator.options.get(CONF_CURVE_STYLE),
            "target_lights": self.coordinator.options.get(
                CONF_LIGHT_ENTITIES, []
            ),
        }
