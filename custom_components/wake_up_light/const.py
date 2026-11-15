"""Constants for the Wake Up Light integration."""

from homeassistant.const import Platform

DOMAIN = "wake_up_light"
PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR, Platform.BUTTON]

CONF_LIGHT_ENTITIES = "light_entities"
CONF_ALARM_SOURCE_TYPE = "alarm_source_type"
CONF_ALARM_ENTITY = "alarm_entity"
CONF_MANUAL_TIME = "manual_time"
CONF_DAYS = "days"
CONF_ENABLED_ENTITY = "enabled_entity"
CONF_DURATION = "duration"
CONF_DURATION_ENTITY = "duration_entity"
CONF_PRE_ALARM_OFFSET = "pre_alarm_offset"
CONF_CURVE_STYLE = "curve_style"
CONF_MAX_BRIGHTNESS = "max_brightness"
CONF_START_BRIGHTNESS = "start_brightness"
CONF_AUTO_OFF_MINUTES = "auto_off_minutes"
CONF_STOP_ON_MANUAL_SWITCH = "stop_on_manual_switch"

# Alarm Source Types
ALARM_SOURCE_INPUT_DATETIME = "input_datetime"
ALARM_SOURCE_SENSOR = "sensor"
ALARM_SOURCE_TIME = "time"
ALARM_SOURCES = [
    ALARM_SOURCE_INPUT_DATETIME,
    ALARM_SOURCE_SENSOR,
    ALARM_SOURCE_TIME,
]

# Curve Styles
CURVE_SUNRISE = "sunrise"
CURVE_WARM = "warm"
CURVE_BRIGHTNESS_ONLY = "brightness_only"
CURVE_STYLES = [
    CURVE_SUNRISE,
    CURVE_WARM,
    CURVE_BRIGHTNESS_ONLY,
]

# Weekdays
WEEKDAY_MON = "mon"
WEEKDAY_TUE = "tue"
WEEKDAY_WED = "wed"
WEEKDAY_THU = "thu"
WEEKDAY_FRI = "fri"
WEEKDAY_SAT = "sat"
WEEKDAY_SUN = "sun"
WEEKDAYS = [
    WEEKDAY_MON,
    WEEKDAY_TUE,
    WEEKDAY_WED,
    WEEKDAY_THU,
    WEEKDAY_FRI,
    WEEKDAY_SAT,
    WEEKDAY_SUN,
]

# Statuses
STATUS_IDLE = "idle"
STATUS_SIMULATING = "simulating"
STATUS_SNOOZED = "snoozed"
STATUS_COMPLETED = "completed"

# Defaults
DEFAULT_NAME = "Wake Up Light"
DEFAULT_DURATION = 15
DEFAULT_MAX_BRIGHTNESS = 100
DEFAULT_START_BRIGHTNESS = 1
DEFAULT_AUTO_OFF_MINUTES = 30
DEFAULT_STEP_SECONDS = 5
DEFAULT_SNOOZE_MINUTES = 9
