"""Lightweight mock for Home Assistant environment during unit tests."""

import asyncio
import sys
import types
from datetime import datetime, timezone
from typing import Any, Callable


class MockState:
    """Mock Home Assistant State."""

    def __init__(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}


class MockStates:
    """Mock Home Assistant States registry."""

    def __init__(self) -> None:
        self._states: dict[str, MockState] = {}

    def get(self, entity_id: str) -> MockState | None:
        return self._states.get(entity_id)

    def set(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self._states[entity_id] = MockState(entity_id, state, attributes)

    def all(self) -> list[MockState]:
        return list(self._states.values())


class MockServices:
    """Mock Home Assistant Services registry."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def async_call(
        self, domain: str, service: str, service_data: dict[str, Any]
    ) -> None:
        self.calls.append((domain, service, service_data))

    def has(self, domain: str, service: str) -> bool:
        return False

    def async_register(
        self, domain: str, service: str, handler: Callable, schema: Any = None
    ) -> None:
        pass


class MockTask:
    """Mock asyncio task."""

    def __init__(self, coro: Any = None) -> None:
        self._coro = coro
        if asyncio.iscoroutine(coro):
            coro.close()

    def done(self) -> bool:
        return False

    def cancel(self) -> None:
        pass


class MockHass:
    """Mock Home Assistant core object."""

    def __init__(self) -> None:
        self.states = MockStates()
        self.services = MockServices()
        self.data: dict[str, Any] = {}

    def async_create_background_task(self, target: Any, name: str) -> Any:
        return MockTask(target)

    def async_create_task(self, target: Any) -> Any:
        return MockTask(target)


def setup_ha_mock():
    """Register mock homeassistant modules in sys.modules."""
    if "homeassistant" in sys.modules:
        return

    ha = types.ModuleType("homeassistant")
    ha.__path__ = []

    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = MockHass
    ha_core.callback = lambda f: f
    ha_core.ServiceCall = Any
    ha.core = ha_core

    ha_util = types.ModuleType("homeassistant.util")
    ha_util.__path__ = []
    ha_dt = types.ModuleType("homeassistant.util.dt")
    ha_dt.now = lambda: datetime.now(timezone.utc)
    ha_dt.as_local = lambda dt: dt
    ha_dt.parse_datetime = lambda s: datetime.fromisoformat(s) if s else None
    ha_util.dt = ha_dt
    ha.util = ha_util

    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_helpers.__path__ = []
    ha_event = types.ModuleType("homeassistant.helpers.event")
    ha_event.async_track_point_in_time = (
        lambda hass, cb, point: (lambda: None)
    )
    ha_helpers.event = ha_event

    ha_selector = types.ModuleType("homeassistant.helpers.selector")

    class Selector:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, val):
            return val

    ha_selector.EntitySelector = Selector
    ha_selector.EntitySelectorConfig = Selector
    ha_selector.SelectSelector = Selector
    ha_selector.SelectSelectorConfig = Selector
    ha_selector.SelectOptionDict = Selector

    class SelectSelectorMode:
        DROPDOWN = "dropdown"
        LIST = "list"

    ha_selector.SelectSelectorMode = SelectSelectorMode
    ha_selector.TimeSelector = Selector
    ha_selector.NumberSelector = Selector
    ha_selector.NumberSelectorConfig = Selector

    class NumberSelectorMode:
        SLIDER = "slider"
        BOX = "box"

    ha_selector.NumberSelectorMode = NumberSelectorMode
    ha_selector.BooleanSelector = Selector
    ha_helpers.selector = ha_selector

    ha_cv = types.ModuleType("homeassistant.helpers.config_validation")
    ha_cv.string = lambda v: str(v)
    ha_cv.boolean = lambda v: bool(v)
    ha_cv.positive_int = lambda v: int(v)
    ha_helpers.config_validation = ha_cv

    ha_devreg = types.ModuleType("homeassistant.helpers.device_registry")

    class DeviceInfo(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    ha_devreg.DeviceInfo = DeviceInfo
    ha_helpers.device_registry = ha_devreg

    ha_entplat = types.ModuleType("homeassistant.helpers.entity_platform")
    ha_entplat.AddEntitiesCallback = Any
    ha_helpers.entity_platform = ha_entplat

    ha.helpers = ha_helpers

    ha_data_entry = types.ModuleType("homeassistant.data_entry_flow")
    ha_data_entry.FlowResult = dict[str, Any]
    ha.data_entry_flow = ha_data_entry

    ha_const = types.ModuleType("homeassistant.const")

    class Platform:
        SWITCH = "switch"
        SENSOR = "sensor"
        BUTTON = "button"

    ha_const.Platform = Platform
    ha.const = ha_const

    ha_config = types.ModuleType("homeassistant.config_entries")
    ha_config.__path__ = []

    class ConfigEntry:
        def __init__(
            self,
            entry_id="test_id",
            data=None,
            options=None,
            title="Test",
        ):
            self.entry_id = entry_id
            self.data = data or {}
            self.options = options or {}
            self.title = title

    ha_config.ConfigEntry = ConfigEntry

    class ConfigFlow:
        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)
            cls.DOMAIN = domain

        def async_show_form(self, step_id, data_schema=None, errors=None):
            return {
                "type": "form",
                "step_id": step_id,
                "errors": errors or {},
            }

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

    class OptionsFlow:
        def async_show_form(self, step_id, data_schema=None, errors=None):
            return {
                "type": "form",
                "step_id": step_id,
                "errors": errors or {},
            }

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

    ha_config.ConfigFlow = ConfigFlow
    ha_config.OptionsFlow = OptionsFlow
    ha.config_entries = ha_config

    ha_components = types.ModuleType("homeassistant.components")
    ha_components.__path__ = []

    ha_switch = types.ModuleType("homeassistant.components.switch")

    class SwitchEntity:
        pass

    ha_switch.SwitchEntity = SwitchEntity
    ha_components.switch = ha_switch

    ha_sensor = types.ModuleType("homeassistant.components.sensor")

    class SensorEntity:
        pass

    class SensorDeviceClass:
        TIMESTAMP = "timestamp"

    ha_sensor.SensorEntity = SensorEntity
    ha_sensor.SensorDeviceClass = SensorDeviceClass
    ha_components.sensor = ha_sensor

    ha_button = types.ModuleType("homeassistant.components.button")

    class ButtonEntity:
        pass

    ha_button.ButtonEntity = ButtonEntity
    ha_components.button = ha_button

    ha.components = ha_components

    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.util"] = ha_util
    sys.modules["homeassistant.util.dt"] = ha_dt
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.event"] = ha_event
    sys.modules["homeassistant.helpers.selector"] = ha_selector
    sys.modules["homeassistant.helpers.config_validation"] = ha_cv
    sys.modules["homeassistant.helpers.device_registry"] = ha_devreg
    sys.modules["homeassistant.helpers.entity_platform"] = ha_entplat
    sys.modules["homeassistant.data_entry_flow"] = ha_data_entry
    sys.modules["homeassistant.const"] = ha_const
    sys.modules["homeassistant.config_entries"] = ha_config
    sys.modules["homeassistant.components"] = ha_components
    sys.modules["homeassistant.components.switch"] = ha_switch
    sys.modules["homeassistant.components.sensor"] = ha_sensor
    sys.modules["homeassistant.components.button"] = ha_button


setup_ha_mock()
