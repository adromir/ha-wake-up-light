"""Unit tests for Wake Up Light calculation engine and coordinator."""

# Establish mock HA environment before importing components
import tests.ha_mock  # noqa: F401

from datetime import datetime, timedelta, timezone
import unittest

from tests.ha_mock import MockHass

from custom_components.wake_up_light.const import (
    ALARM_SOURCE_INPUT_DATETIME,
    CONF_ALARM_ENTITY,
    CONF_ALARM_SOURCE_TYPE,
    CONF_DURATION,
    CONF_DURATION_ENTITY,
    CONF_ENABLED_ENTITY,
    CONF_LIGHT_ENTITIES,
    CURVE_BRIGHTNESS_ONLY,
    CURVE_SUNRISE,
    CURVE_WARM,
    STATUS_SIMULATING,
    STATUS_SNOOZED,
)
from custom_components.wake_up_light.simulator import (
    WakeUpLightCoordinator,
    calculate_brightness,
    calculate_kelvin,
    calculate_rgb,
)


class TestWakeUpLightSimulator(unittest.TestCase):
    """Test suite for math curves and coordinator logic."""

    def test_calculate_brightness_quadratic_easing(self):
        """Test quadratic easing ensures gentle start and accurate max."""
        # At 0.0 -> start_pct (1%) -> min 3 in 0-255 scale
        b_0 = calculate_brightness(0.0, start_pct=1, max_pct=100)
        self.assertGreaterEqual(b_0, 1)
        self.assertLessEqual(b_0, 10)

        # At 0.5 -> (0.5^2) = 0.25 (only 25% of the ramp at 50% time)
        b_half = calculate_brightness(0.5, start_pct=1, max_pct=100)
        # Expected pct: 1 + 99 * 0.25 = 25.75% -> ~66/255
        self.assertTrue(50 <= b_half <= 75)

        # At 1.0 -> max_pct (100%) -> 255
        b_1 = calculate_brightness(1.0, start_pct=1, max_pct=100)
        self.assertEqual(b_1, 255)

        # Clamping
        self.assertEqual(calculate_brightness(-0.5), b_0)
        self.assertEqual(calculate_brightness(1.5), 255)

    def test_calculate_kelvin(self):
        """Test Kelvin calculation across sunrise and warm curves."""
        # Sunrise curve
        k_start = calculate_kelvin(0.0, CURVE_SUNRISE)
        k_end = calculate_kelvin(1.0, CURVE_SUNRISE)
        self.assertEqual(k_start, 2000)
        self.assertEqual(k_end, 4800)

        # Warm curve
        k_warm_end = calculate_kelvin(1.0, CURVE_WARM)
        self.assertEqual(k_warm_end, 3000)

    def test_calculate_rgb(self):
        """Test RGB interpolation for non-kelvin lights."""
        rgb_start = calculate_rgb(0.0, CURVE_SUNRISE)
        self.assertEqual(rgb_start[0], 255)
        self.assertLess(rgb_start[2], 10)  # Almost no blue at start

        rgb_end = calculate_rgb(1.0, CURVE_SUNRISE)
        self.assertEqual(rgb_end[0], 255)
        self.assertGreater(rgb_end[2], 200)  # Crisp daylight blue at finish

        # Brightness only returns pure white
        rgb_bo = calculate_rgb(0.5, CURVE_BRIGHTNESS_ONLY)
        self.assertEqual(rgb_bo, (255, 255, 255))

    def test_coordinator_dynamic_duration(self):
        """Test duration resolution via options or dynamic helper entity."""
        hass = MockHass()
        options = {
            CONF_LIGHT_ENTITIES: ["light.bedroom"],
            CONF_DURATION: 20,
            CONF_DURATION_ENTITY: "input_number.sunrise_duration",
        }
        coord = WakeUpLightCoordinator(hass, "test_entry", options)

        # When entity is not in state machine, falls back to CONF_DURATION
        self.assertEqual(coord.get_duration_minutes(), 20)

        # When entity exists with value 15.0
        hass.states.set("input_number.sunrise_duration", "15.0")
        self.assertEqual(coord.get_duration_minutes(), 15)

    def test_coordinator_is_enabled_by_helper(self):
        """Test master enable switch/helper check."""
        hass = MockHass()
        options = {
            CONF_LIGHT_ENTITIES: ["light.bedroom"],
            CONF_ENABLED_ENTITY: "input_boolean.wecker_aktiv",
        }
        coord = WakeUpLightCoordinator(hass, "test_entry", options)

        # Entity not yet created -> defaults to enabled
        self.assertTrue(coord.is_enabled_by_helper())

        hass.states.set("input_boolean.wecker_aktiv", "off")
        self.assertFalse(coord.is_enabled_by_helper())

        hass.states.set("input_boolean.wecker_aktiv", "on")
        self.assertTrue(coord.is_enabled_by_helper())

    def test_coordinator_alarm_resolution_input_datetime(self):
        """Test alarm resolution from input_datetime helper."""
        hass = MockHass()
        options = {
            CONF_LIGHT_ENTITIES: ["light.bedroom"],
            CONF_ALARM_SOURCE_TYPE: ALARM_SOURCE_INPUT_DATETIME,
            CONF_ALARM_ENTITY: "input_datetime.wake_time",
            CONF_DURATION: 15,
        }
        coord = WakeUpLightCoordinator(hass, "test_entry", options)

        # Target 2 hours from now
        now = datetime.now(timezone.utc)
        target = now + timedelta(hours=2)
        hass.states.set(
            "input_datetime.wake_time",
            f"{target.hour:02d}:{target.minute:02d}:00",
            {
                "hour": target.hour,
                "minute": target.minute,
                "has_date": False,
                "has_time": True,
            },
        )

        alarm_dt = coord.resolve_next_alarm()
        self.assertIsNotNone(alarm_dt)
        self.assertEqual(alarm_dt.hour, target.hour)
        self.assertEqual(alarm_dt.minute, target.minute)

        # Reschedule check
        coord.reschedule()
        self.assertIsNotNone(coord.next_alarm)
        self.assertIsNotNone(coord.next_start_time)
        expected_start = coord.next_alarm - timedelta(minutes=15)
        self.assertEqual(coord.next_start_time, expected_start)

    def test_coordinator_snooze(self):
        """Test snooze functionality."""
        hass = MockHass()
        hass.states.set(
            "light.bedroom",
            "on",
            {"supported_color_modes": ["color_temp_kelvin"]},
        )
        options = {
            CONF_LIGHT_ENTITIES: ["light.bedroom"],
            CONF_DURATION: 10,
        }
        coord = WakeUpLightCoordinator(hass, "test_entry", options)
        coord.async_start_simulation()
        self.assertEqual(coord.status, STATUS_SIMULATING)

        coord.async_snooze(minutes=9)
        self.assertEqual(coord.status, STATUS_SNOOZED)
        self.assertEqual(coord.progress, 0.0)


if __name__ == "__main__":
    unittest.main()
