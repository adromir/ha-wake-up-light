"""Config flow and Options flow for Wake Up Light."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    ALARM_SOURCE_INPUT_DATETIME,
    ALARM_SOURCE_SENSOR,
    ALARM_SOURCE_TIME,
    ALARM_SOURCES,
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
    CURVE_STYLES,
    CURVE_SUNRISE,
    DEFAULT_AUTO_OFF_MINUTES,
    DEFAULT_DURATION,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_NAME,
    DEFAULT_START_BRIGHTNESS,
    DOMAIN,
    WEEKDAYS,
)

_LOGGER = logging.getLogger(__name__)


def build_schema(options: dict[str, Any] | None = None) -> vol.Schema:
    """Build configuration schema with dynamic selectors."""
    opts = options or {}

    return vol.Schema(
        {
            vol.Required(
                CONF_LIGHT_ENTITIES,
                default=opts.get(CONF_LIGHT_ENTITIES, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            ),
            vol.Required(
                CONF_ALARM_SOURCE_TYPE,
                default=opts.get(CONF_ALARM_SOURCE_TYPE, ALARM_SOURCE_INPUT_DATETIME),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=s, label=s)
                        for s in ALARM_SOURCES
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_ALARM_SOURCE_TYPE,
                )
            ),
            vol.Optional(
                CONF_ALARM_ENTITY,
                description={"suggested_value": opts.get(CONF_ALARM_ENTITY)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["input_datetime", "sensor"])
            ),
            vol.Optional(
                CONF_MANUAL_TIME,
                default=opts.get(CONF_MANUAL_TIME, "07:00:00"),
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_DAYS,
                default=opts.get(CONF_DAYS, WEEKDAYS),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=d, label=d)
                        for d in WEEKDAYS
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                    translation_key="days",
                )
            ),
            vol.Required(
                CONF_DURATION,
                default=opts.get(CONF_DURATION, DEFAULT_DURATION),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=60,
                    step=1,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional(
                CONF_DURATION_ENTITY,
                description={"suggested_value": opts.get(CONF_DURATION_ENTITY)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["input_number", "number"])
            ),
            vol.Optional(
                CONF_ENABLED_ENTITY,
                description={"suggested_value": opts.get(CONF_ENABLED_ENTITY)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["input_boolean", "switch"])
            ),
            vol.Required(
                CONF_CURVE_STYLE,
                default=opts.get(CONF_CURVE_STYLE, CURVE_SUNRISE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=c, label=c)
                        for c in CURVE_STYLES
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_CURVE_STYLE,
                )
            ),
            vol.Required(
                CONF_START_BRIGHTNESS,
                default=opts.get(CONF_START_BRIGHTNESS, DEFAULT_START_BRIGHTNESS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=25,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_MAX_BRIGHTNESS,
                default=opts.get(CONF_MAX_BRIGHTNESS, DEFAULT_MAX_BRIGHTNESS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_AUTO_OFF_MINUTES,
                default=opts.get(CONF_AUTO_OFF_MINUTES, DEFAULT_AUTO_OFF_MINUTES),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=120,
                    step=5,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_STOP_ON_MANUAL_SWITCH,
                default=opts.get(CONF_STOP_ON_MANUAL_SWITCH, True),
            ): selector.BooleanSelector(),
        }
    )


class WakeUpLightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wake Up Light."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            lights = user_input.get(CONF_LIGHT_ENTITIES, [])
            if not lights:
                errors[CONF_LIGHT_ENTITIES] = "no_lights_selected"

            source = user_input.get(CONF_ALARM_SOURCE_TYPE)
            if source in (ALARM_SOURCE_INPUT_DATETIME, ALARM_SOURCE_SENSOR):
                if not user_input.get(CONF_ALARM_ENTITY):
                    errors[CONF_ALARM_ENTITY] = "no_alarm_entity_selected"

            if not errors:
                title = DEFAULT_NAME
                if len(lights) == 1:
                    st = self.hass.states.get(lights[0])
                    if st and st.attributes.get("friendly_name"):
                        title = f"Wake Up Light ({st.attributes['friendly_name']})"

                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=build_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return WakeUpLightOptionsFlow(config_entry)


class WakeUpLightOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for live reconfiguration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            lights = user_input.get(CONF_LIGHT_ENTITIES, [])
            if not lights:
                errors[CONF_LIGHT_ENTITIES] = "no_lights_selected"

            source = user_input.get(CONF_ALARM_SOURCE_TYPE)
            if source in (ALARM_SOURCE_INPUT_DATETIME, ALARM_SOURCE_SENSOR):
                if not user_input.get(CONF_ALARM_ENTITY):
                    errors[CONF_ALARM_ENTITY] = "no_alarm_entity_selected"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        merged = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=build_schema(merged),
            errors=errors,
        )
