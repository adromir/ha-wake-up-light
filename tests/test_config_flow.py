"""Unit tests for Wake Up Light Config Flow and Options Flow."""

import tests.ha_mock  # noqa: F401

import asyncio
import unittest
from unittest.mock import MagicMock

from tests.ha_mock import MockHass

# Mock voluptuous and selector validation if needed
import voluptuous as vol

from custom_components.wake_up_light.const import (
    ALARM_SOURCE_INPUT_DATETIME,
    CONF_ALARM_ENTITY,
    CONF_ALARM_SOURCE_TYPE,
    CONF_LIGHT_ENTITIES,
    DOMAIN,
)
from custom_components.wake_up_light.config_flow import (
    WakeUpLightConfigFlow,
    WakeUpLightOptionsFlow,
    build_schema,
)


class TestConfigFlow(unittest.TestCase):
    """Test config and options flow validation."""

    def setUp(self):
        self.hass = MockHass()

    def test_build_schema_defaults(self):
        """Test build_schema returns expected keys."""
        schema = build_schema()
        self.assertIsNotNone(schema)
        # Check that schema defines expected field markers
        keys = [k.schema if hasattr(k, "schema") else str(k) for k in schema.schema.keys()]
        self.assertIn(CONF_LIGHT_ENTITIES, keys)
        self.assertIn(CONF_ALARM_SOURCE_TYPE, keys)

    def test_config_flow_missing_lights(self):
        """Test validation error when no lights are provided."""
        flow = WakeUpLightConfigFlow()
        flow.hass = self.hass

        result = asyncio.run(
            flow.async_step_user(
                {
                    CONF_LIGHT_ENTITIES: [],
                    CONF_ALARM_SOURCE_TYPE: ALARM_SOURCE_INPUT_DATETIME,
                    CONF_ALARM_ENTITY: "input_datetime.wake",
                }
            )
        )
        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_LIGHT_ENTITIES, result["errors"])

    def test_config_flow_missing_alarm_entity(self):
        """Test validation error when alarm source requires an entity but none is given."""
        flow = WakeUpLightConfigFlow()
        flow.hass = self.hass

        result = asyncio.run(
            flow.async_step_user(
                {
                    CONF_LIGHT_ENTITIES: ["light.bedroom"],
                    CONF_ALARM_SOURCE_TYPE: ALARM_SOURCE_INPUT_DATETIME,
                    CONF_ALARM_ENTITY: "",
                }
            )
        )
        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_ALARM_ENTITY, result["errors"])

    def test_config_flow_valid_creation(self):
        """Test successful entry creation with valid parameters."""
        flow = WakeUpLightConfigFlow()
        flow.hass = self.hass
        self.hass.states.set("light.bedroom", "off", {"friendly_name": "Bedroom Ceiling"})

        result = asyncio.run(
            flow.async_step_user(
                {
                    CONF_LIGHT_ENTITIES: ["light.bedroom"],
                    CONF_ALARM_SOURCE_TYPE: ALARM_SOURCE_INPUT_DATETIME,
                    CONF_ALARM_ENTITY: "input_datetime.wake",
                }
            )
        )
        self.assertEqual(result["type"], "create_entry")
        self.assertIn("Bedroom Ceiling", result["title"])


if __name__ == "__main__":
    unittest.main()
