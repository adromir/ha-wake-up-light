"""Sensor platform for Wake Up Light."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATUS_SIMULATING
from .simulator import WakeUpLightCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Wake Up Light sensors."""
    coordinator: WakeUpLightCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WakeUpLightStatusSensor(coordinator, entry),
            WakeUpLightProgressSensor(coordinator, entry),
            WakeUpLightNextStartSensor(coordinator, entry),
        ]
    )


class WakeUpLightStatusSensor(SensorEntity):
    """Sensor displaying the current state of the simulation."""

    _attr_has_entity_name = True
    _attr_translation_key = "status"

    def __init__(self, coordinator: WakeUpLightCoordinator, entry: ConfigEntry) -> None:
        """Initialize status sensor."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sensor_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Adromir",
            model="Sunrise Gradient Engine",
        )

    async def async_added_to_hass(self) -> None:
        """Register coordinator update callbacks."""
        self.async_on_remove(self.coordinator.register_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator state updates."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Return status string."""
        return self.coordinator.status

    @property
    def icon(self) -> str:
        """Dynamic icon depending on simulation state."""
        if self.coordinator.status == STATUS_SIMULATING:
            return "mdi:weather-sunset-up"
        return "mdi:weather-sunset"


class WakeUpLightProgressSensor(SensorEntity):
    """Sensor displaying the current sunrise progress percentage."""

    _attr_has_entity_name = True
    _attr_translation_key = "progress"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:progress-clock"

    def __init__(self, coordinator: WakeUpLightCoordinator, entry: ConfigEntry) -> None:
        """Initialize progress sensor."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sensor_progress"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Adromir",
            model="Sunrise Gradient Engine",
        )

    async def async_added_to_hass(self) -> None:
        """Register coordinator update callbacks."""
        self.async_on_remove(self.coordinator.register_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator state updates."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        """Return current progress percentage."""
        return self.coordinator.progress


class WakeUpLightNextStartSensor(SensorEntity):
    """Sensor displaying the next scheduled sunrise start timestamp."""

    _attr_has_entity_name = True
    _attr_translation_key = "next_start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator: WakeUpLightCoordinator, entry: ConfigEntry) -> None:
        """Initialize timestamp sensor."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sensor_next_start"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Adromir",
            model="Sunrise Gradient Engine",
        )

    async def async_added_to_hass(self) -> None:
        """Register coordinator update callbacks."""
        self.async_on_remove(self.coordinator.register_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator state updates."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | None:
        """Return next start datetime."""
        return self.coordinator.next_start_time
