"""Calculation and simulation engine for Wake Up Light."""

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
import homeassistant.util.dt as dt_util

from .const import (
    ALARM_SOURCE_INPUT_DATETIME,
    ALARM_SOURCE_SENSOR,
    ALARM_SOURCE_TIME,
    CONF_ALARM_ENTITY,
    CONF_ALARM_SOURCE_TYPE,
    CONF_AUTO_OFF_MINUTES,
    CONF_CURVE_STYLE,
    CONF_DAYS,
    CONF_DURATION,
    CONF_DURATION_ENTITY,
    CONF_ENABLED_ENTITY,
    CONF_LIGHT_ENTITIES,
    CONF_MANUAL_TIME,
    CONF_MAX_BRIGHTNESS,
    CONF_PRE_ALARM_OFFSET,
    CONF_START_BRIGHTNESS,
    CONF_STOP_ON_MANUAL_SWITCH,
    CURVE_BRIGHTNESS_ONLY,
    CURVE_SUNRISE,
    CURVE_WARM,
    DEFAULT_AUTO_OFF_MINUTES,
    DEFAULT_DURATION,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_SNOOZE_MINUTES,
    DEFAULT_START_BRIGHTNESS,
    DEFAULT_STEP_SECONDS,
    STATUS_COMPLETED,
    STATUS_IDLE,
    STATUS_SIMULATING,
    STATUS_SNOOZED,
    WEEKDAYS,
)

_LOGGER = logging.getLogger(__name__)


def calculate_brightness(
    progress: float, start_pct: int = 1, max_pct: int = 100
) -> int:
    """Calculate brightness (1-255) based on quadratic easing.

    Eye sensitivity to light is logarithmic; quadratic easing ensures a soft,
    gentle ramp up at low intensities without sudden perception jumps.
    """
    clamped_progress = max(0.0, min(1.0, progress))
    curve = clamped_progress ** 2
    pct = start_pct + (max_pct - start_pct) * curve
    return int(round(max(1, min(255, (pct / 100.0) * 255.0))))


def calculate_kelvin(
    progress: float, curve_style: str = CURVE_SUNRISE
) -> int:
    """Calculate Kelvin color temperature for the current progress."""
    clamped = max(0.0, min(1.0, progress))
    if curve_style == CURVE_WARM:
        # 2000K (candlelight/deep amber) -> 3000K (warm white)
        return int(round(2000 + (1000 * (clamped ** 1.3))))
    # CURVE_SUNRISE: 2000K (deep dawn) -> 4800K (crisp wake-up daylight)
    return int(round(2000 + (2800 * (clamped ** 1.4))))


def calculate_rgb(
    progress: float, curve_style: str = CURVE_SUNRISE
) -> tuple[int, int, int]:
    """Calculate RGB color for lights without native Kelvin support."""
    clamped = max(0.0, min(1.0, progress))
    if curve_style == CURVE_BRIGHTNESS_ONLY:
        return (255, 255, 255)

    if clamped < 0.35:
        # Deep Red -> Warm Amber
        ratio = clamped / 0.35
        r = 255
        g = int(round(25 + (115 * ratio)))
        b = 0
    elif clamped < 0.7:
        # Warm Amber -> Warm White
        ratio = (clamped - 0.35) / 0.35
        r = 255
        g = int(round(140 + (75 * ratio)))
        b = int(round(60 * ratio))
    else:
        # Warm White -> Soft Daylight White
        ratio = (clamped - 0.7) / 0.3
        r = 255
        g = int(round(215 + (40 * ratio)))
        b = int(round(60 + (180 * ratio)))

    return (min(255, r), min(255, g), min(255, b))


class WakeUpLightCoordinator:
    """Coordinator managing alarm checking, timers, and simulation loop."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, options: dict[str, Any]
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry_id = entry_id
        self.options = options
        self.enabled = True
        self.status = STATUS_IDLE
        self.progress: float = 0.0
        self.next_alarm: datetime | None = None
        self.next_start_time: datetime | None = None

        self._simulation_task: asyncio.Task | None = None
        self._check_unsub: Any = None
        self._auto_off_unsub: Any = None
        self._listeners: list[callback] = []
        self._sent_light_states: dict[str, dict[str, Any]] = {}

    def update_options(self, options: dict[str, Any]) -> None:
        """Update coordinator options on reconfigure."""
        self.options = options
        self.reschedule()

    def register_listener(self, update_cb: callback) -> callback:
        """Register a callback for status updates."""
        self._listeners.append(update_cb)

        def unsub() -> None:
            if update_cb in self._listeners:
                self._listeners.remove(update_cb)

        return unsub

    def _notify_listeners(self) -> None:
        """Notify registered entity listeners to push state updates."""
        for cb in list(self._listeners):
            try:
                cb()
            except Exception as err:
                _LOGGER.debug("Error notifying listener: %s", err)

    def get_duration_minutes(self) -> int:
        """Get configured duration in minutes, resolving helper entity."""
        duration_entity = self.options.get(CONF_DURATION_ENTITY)
        if duration_entity and self.hass.states.get(duration_entity):
            try:
                val = float(self.hass.states.get(duration_entity).state)
                if val > 0:
                    return int(round(val))
            except (ValueError, TypeError):
                pass
        return int(self.options.get(CONF_DURATION, DEFAULT_DURATION))

    def is_enabled_by_helper(self) -> bool:
        """Check if optional master enable helper allows the simulation."""
        enabled_entity = self.options.get(CONF_ENABLED_ENTITY)
        if not enabled_entity or not self.hass.states.get(enabled_entity):
            return True
        st = self.hass.states.get(enabled_entity).state.lower()
        return st in ("on", "true", "home", "1")

    def resolve_next_alarm(self) -> datetime | None:
        """Resolve next alarm time from the configured source."""
        source_type = self.options.get(
            CONF_ALARM_SOURCE_TYPE, ALARM_SOURCE_INPUT_DATETIME
        )
        now = dt_util.now()

        # 1. Input Datetime Source
        if source_type == ALARM_SOURCE_INPUT_DATETIME:
            entity_id = self.options.get(CONF_ALARM_ENTITY)
            if not entity_id:
                return None
            state_obj = self.hass.states.get(entity_id)
            if not state_obj or state_obj.state in ("unknown", "unavailable"):
                return None

            attr = state_obj.attributes
            has_date = attr.get("has_date", False)
            has_time = attr.get("has_time", True)

            # Full timestamp
            if has_date and has_time and attr.get("year"):
                try:
                    dt = datetime(
                        attr["year"],
                        attr["month"],
                        attr["day"],
                        attr.get("hour", 0),
                        attr.get("minute", 0),
                        attr.get("second", 0),
                        tzinfo=now.tzinfo,
                    )
                    return dt if dt > now else None
                except Exception:
                    pass

            # Time only
            h = attr.get("hour")
            m = attr.get("minute")
            if h is None or m is None:
                try:
                    parts = [int(p) for p in state_obj.state.split(":")[:2]]
                    h, m = parts[0], parts[1]
                except Exception:
                    return None

            target_today = now.replace(
                hour=h, minute=m, second=0, microsecond=0
            )
            if target_today > now:
                return target_today
            return target_today + timedelta(days=1)

        # 2. Next Alarm Sensor (e.g. Companion App / Alexa)
        if source_type == ALARM_SOURCE_SENSOR:
            entity_id = self.options.get(CONF_ALARM_ENTITY)
            if not entity_id:
                return None
            state_obj = self.hass.states.get(entity_id)
            if not state_obj or state_obj.state in ("unknown", "unavailable"):
                return None

            ts_str = state_obj.state
            if state_obj.attributes.get("next_alarm"):
                ts_str = state_obj.attributes["next_alarm"]

            parsed = dt_util.parse_datetime(ts_str)
            if parsed and parsed > now:
                return dt_util.as_local(parsed)
            return None

        # 3. Fixed Manual Time & Weekdays
        if source_type == ALARM_SOURCE_TIME:
            time_str = self.options.get(CONF_MANUAL_TIME, "07:00")
            try:
                parts = [int(p) for p in time_str.split(":")[:2]]
                h, m = parts[0], parts[1]
            except Exception:
                return None

            selected_days = self.options.get(CONF_DAYS, WEEKDAYS)
            day_map = {
                0: "mon",
                1: "tue",
                2: "wed",
                3: "thu",
                4: "fri",
                5: "sat",
                6: "sun",
            }

            for day_offset in range(8):
                candidate = (now + timedelta(days=day_offset)).replace(
                    hour=h, minute=m, second=0, microsecond=0
                )
                if candidate > now:
                    day_slug = day_map.get(candidate.weekday())
                    if not selected_days or day_slug in selected_days:
                        return candidate

        return None

    def reschedule(self) -> None:
        """Cancel existing schedule and set up the next check/run."""
        if self._check_unsub:
            self._check_unsub()
            self._check_unsub = None

        if not self.enabled:
            self.next_alarm = None
            self.next_start_time = None
            self._notify_listeners()
            return

        alarm_dt = self.resolve_next_alarm()
        self.next_alarm = alarm_dt

        if not alarm_dt:
            self.next_start_time = None
            # Recheck every 5 minutes if alarm cannot be resolved right now
            self._check_unsub = async_track_point_in_time(
                self.hass,
                self._async_timer_tick,
                dt_util.now() + timedelta(minutes=5),
            )
            self._notify_listeners()
            return

        duration_min = self.get_duration_minutes()
        offset_min = self.options.get(CONF_PRE_ALARM_OFFSET)
        if offset_min is None or offset_min < 0:
            offset_min = duration_min

        start_dt = alarm_dt - timedelta(minutes=offset_min)
        self.next_start_time = start_dt

        now = dt_util.now()
        if start_dt <= now:
            # If start time passed but alarm has not, start immediately
            if alarm_dt > now and self.status == STATUS_IDLE:
                self.async_start_simulation()
                return
            wake_target = alarm_dt + timedelta(seconds=10)
        else:
            wake_target = start_dt

        self._check_unsub = async_track_point_in_time(
            self.hass, self._async_timer_tick, wake_target
        )
        self._notify_listeners()

    @callback
    def _async_timer_tick(self, _now: datetime) -> None:
        """Called when scheduled start time arrives."""
        self._check_unsub = None
        now = dt_util.now()

        if self.enabled and self.is_enabled_by_helper():
            if (
                self.next_start_time
                and abs((self.next_start_time - now).total_seconds()) < 90
            ):
                self.async_start_simulation()
                return

        self.reschedule()

    def async_start_simulation(self) -> None:
        """Start the sunrise light simulation loop."""
        if self._simulation_task and not self._simulation_task.done():
            self._simulation_task.cancel()

        self.status = STATUS_SIMULATING
        self.progress = 0.0
        self._notify_listeners()
        self._simulation_task = self.hass.async_create_background_task(
            self._simulation_loop(), "wake_up_light_simulation"
        )

    def async_stop_simulation(self, turn_off_lights: bool = False) -> None:
        """Stop/cancel the running simulation."""
        if self._simulation_task and not self._simulation_task.done():
            self._simulation_task.cancel()
            self._simulation_task = None

        if self._auto_off_unsub:
            self._auto_off_unsub()
            self._auto_off_unsub = None

        self.status = STATUS_IDLE
        self.progress = 0.0

        if turn_off_lights:
            lights = self.options.get(CONF_LIGHT_ENTITIES, [])
            for light_id in lights:
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "light", "turn_off", {"entity_id": light_id}
                    )
                )

        self._notify_listeners()
        self.reschedule()

    def async_snooze(self, minutes: int = DEFAULT_SNOOZE_MINUTES) -> None:
        """Snooze the light: dims down and restarts after given delay."""
        if self._simulation_task and not self._simulation_task.done():
            self._simulation_task.cancel()
            self._simulation_task = None

        self.status = STATUS_SNOOZED
        self.progress = 0.0

        # Dim lights down to minimal amber glow
        lights = self.options.get(CONF_LIGHT_ENTITIES, [])
        for light_id in lights:
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "light",
                    "turn_on",
                    {
                        "entity_id": light_id,
                        "brightness": 5,
                        "transition": 2,
                    },
                )
            )

        self._notify_listeners()

        @callback
        def _wake_after_snooze(_now: datetime) -> None:
            self.async_start_simulation()

        self._check_unsub = async_track_point_in_time(
            self.hass,
            _wake_after_snooze,
            dt_util.now() + timedelta(minutes=minutes),
        )

    async def _simulation_loop(self) -> None:
        """Perform step-by-step sunrise fading."""
        duration_sec = self.get_duration_minutes() * 60
        if duration_sec <= 0:
            duration_sec = 60

        step_sec = DEFAULT_STEP_SECONDS
        total_steps = max(1, int(round(duration_sec / step_sec)))

        start_pct = int(
            self.options.get(CONF_START_BRIGHTNESS, DEFAULT_START_BRIGHTNESS)
        )
        max_pct = int(
            self.options.get(CONF_MAX_BRIGHTNESS, DEFAULT_MAX_BRIGHTNESS)
        )
        curve_style = self.options.get(CONF_CURVE_STYLE, CURVE_SUNRISE)
        lights = self.options.get(CONF_LIGHT_ENTITIES, [])
        stop_on_switch = self.options.get(CONF_STOP_ON_MANUAL_SWITCH, True)

        _LOGGER.debug(
            "Starting wake-up light for %s over %d seconds in %d steps",
            lights,
            duration_sec,
            total_steps,
        )

        try:
            for step in range(total_steps + 1):
                progress = min(1.0, step / total_steps)
                self.progress = round(progress * 100.0, 1)

                brightness = calculate_brightness(progress, start_pct, max_pct)
                kelvin = calculate_kelvin(progress, curve_style)
                rgb = calculate_rgb(progress, curve_style)

                for light_id in lights:
                    st = self.hass.states.get(light_id)
                    if not st:
                        continue

                    # Abort if manually turned off
                    if stop_on_switch and step > 1 and st.state == "off":
                        _LOGGER.info(
                            "Wake-up light aborted: %s turned off", light_id
                        )
                        self.status = STATUS_IDLE
                        self._notify_listeners()
                        self.reschedule()
                        return

                    service_data: dict[str, Any] = {
                        "entity_id": light_id,
                        "brightness": brightness,
                        "transition": step_sec,
                    }

                    modes = st.attributes.get("supported_color_modes") or []
                    if curve_style != CURVE_BRIGHTNESS_ONLY:
                        if (
                            "color_temp" in modes
                            or "color_temp_kelvin" in modes
                        ):
                            service_data["color_temp_kelvin"] = kelvin
                        elif any(m in modes for m in ("rgb", "rgbw", "rgbww")):
                            service_data["rgb_color"] = rgb

                    try:
                        await self.hass.services.async_call(
                            "light", "turn_on", service_data
                        )
                    except Exception as err:
                        _LOGGER.debug(
                            "Error updating light %s: %s", light_id, err
                        )

                self._notify_listeners()

                if progress >= 1.0:
                    break

                await asyncio.sleep(step_sec)

            self.status = STATUS_COMPLETED
            self._notify_listeners()

            # Handle Auto-Off
            auto_off_min = int(
                self.options.get(
                    CONF_AUTO_OFF_MINUTES, DEFAULT_AUTO_OFF_MINUTES
                )
            )
            if auto_off_min > 0:
                @callback
                def _auto_turn_off(_now: datetime) -> None:
                    self.async_stop_simulation(turn_off_lights=True)

                self._auto_off_unsub = async_track_point_in_time(
                    self.hass,
                    _auto_turn_off,
                    dt_util.now() + timedelta(minutes=auto_off_min),
                )

        except asyncio.CancelledError:
            _LOGGER.debug("Wake up light simulation was cancelled")
            raise
        except Exception as err:
            _LOGGER.error("Error in wake up light simulation loop: %s", err)
            self.status = STATUS_IDLE
            self._notify_listeners()
            self.reschedule()
