"""
Options flow schemas.

Schemas for the options flow that allows users to modify settings
after initial configuration.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.smart_venetian_blinds.const import (
    CONF_CHANGE_THRESHOLD,
    CONF_MIN_UPDATE_INTERVAL,
    CONF_POSITION_SETTLING_DELAY,
    CONF_POSITION_TIMEOUT,
    CONF_SEASON_END,
    CONF_SEASON_PAUSE_ENABLED,
    CONF_SEASON_REST_POSITION,
    CONF_SEASON_START,
    DEFAULT_CHANGE_THRESHOLD,
    DEFAULT_MIN_UPDATE_INTERVAL,
    DEFAULT_POSITION_SETTLING_DELAY,
    DEFAULT_POSITION_TIMEOUT,
)
from custom_components.smart_venetian_blinds.season import SeasonWindow, day_choices
from homeassistant.helpers import selector


def _day_selector(language: str | None) -> selector.SelectSelector:
    """
    Return a dropdown listing every possible season boundary.

    Home Assistant has no month/day selector, and a date picker would show a year
    that carries no meaning and does not survive a round trip. A select stores a
    language-independent ``MM-DD`` value while showing a localized label.
    """
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[selector.SelectOptionDict(value=value, label=label) for value, label in day_choices(language)],
            mode=selector.SelectSelectorMode.DROPDOWN,
            custom_value=False,
        ),
    )


def get_season_schema(
    defaults: Mapping[str, Any] | None = None,
    language: str | None = None,
) -> vol.Schema:
    """
    Get schema for the seasonal pause options.

    Args:
        defaults: Optional dictionary of current option values.
        language: Home Assistant's configured language, used for the day labels.

    Returns:
        Voluptuous schema for seasonal pause configuration.
    """
    defaults = defaults or {}
    season = SeasonWindow.from_options(defaults)
    return vol.Schema(
        {
            vol.Required(
                CONF_SEASON_PAUSE_ENABLED,
                default=season.enabled,
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_SEASON_START,
                default=season.start_value,
            ): _day_selector(language),
            vol.Required(
                CONF_SEASON_END,
                default=season.end_value,
            ): _day_selector(language),
            vol.Required(
                CONF_SEASON_REST_POSITION,
                default=season.rest_position,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        },
    )


def get_options_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """
    Get schema for options flow.

    Args:
        defaults: Optional dictionary of current option values.

    Returns:
        Voluptuous schema for options configuration.
    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_CHANGE_THRESHOLD,
                default=defaults.get(CONF_CHANGE_THRESHOLD, DEFAULT_CHANGE_THRESHOLD),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=30,
                    step=1,
                    unit_of_measurement="°",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_MIN_UPDATE_INTERVAL,
                default=defaults.get(CONF_MIN_UPDATE_INTERVAL, DEFAULT_MIN_UPDATE_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=600,
                    step=10,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_POSITION_TIMEOUT,
                default=defaults.get(CONF_POSITION_TIMEOUT, DEFAULT_POSITION_TIMEOUT),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=300,
                    step=5,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_POSITION_SETTLING_DELAY,
                default=defaults.get(CONF_POSITION_SETTLING_DELAY, DEFAULT_POSITION_SETTLING_DELAY),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=30,
                    step=1,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        },
    )


__all__ = [
    "get_options_schema",
    "get_season_schema",
]
