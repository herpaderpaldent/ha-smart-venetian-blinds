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
    CONF_SEASON_END_DAY,
    CONF_SEASON_END_MONTH,
    CONF_SEASON_PAUSE_ENABLED,
    CONF_SEASON_REST_POSITION,
    CONF_SEASON_START_DAY,
    CONF_SEASON_START_MONTH,
    DEFAULT_CHANGE_THRESHOLD,
    DEFAULT_MIN_UPDATE_INTERVAL,
    DEFAULT_POSITION_SETTLING_DELAY,
    DEFAULT_POSITION_TIMEOUT,
    DEFAULT_SEASON_END_DAY,
    DEFAULT_SEASON_END_MONTH,
    DEFAULT_SEASON_PAUSE_ENABLED,
    DEFAULT_SEASON_REST_POSITION,
    DEFAULT_SEASON_START_DAY,
    DEFAULT_SEASON_START_MONTH,
)
from homeassistant.helpers import selector

_MONTH_VALUES = [str(month) for month in range(1, 13)]


def _month_selector() -> selector.SelectSelector:
    """Return a dropdown selector for a calendar month."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=_MONTH_VALUES,
            mode=selector.SelectSelectorMode.DROPDOWN,
            translation_key="month",
        ),
    )


def _day_selector() -> selector.NumberSelector:
    """Return a box selector for a day of month."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1,
            max=31,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
        ),
    )


def get_season_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """
    Get schema for the seasonal pause options.

    Args:
        defaults: Optional dictionary of current option values.

    Returns:
        Voluptuous schema for seasonal pause configuration.
    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_SEASON_PAUSE_ENABLED,
                default=defaults.get(CONF_SEASON_PAUSE_ENABLED, DEFAULT_SEASON_PAUSE_ENABLED),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_SEASON_START_MONTH,
                default=str(defaults.get(CONF_SEASON_START_MONTH, DEFAULT_SEASON_START_MONTH)),
            ): _month_selector(),
            vol.Required(
                CONF_SEASON_START_DAY,
                default=defaults.get(CONF_SEASON_START_DAY, DEFAULT_SEASON_START_DAY),
            ): _day_selector(),
            vol.Required(
                CONF_SEASON_END_MONTH,
                default=str(defaults.get(CONF_SEASON_END_MONTH, DEFAULT_SEASON_END_MONTH)),
            ): _month_selector(),
            vol.Required(
                CONF_SEASON_END_DAY,
                default=defaults.get(CONF_SEASON_END_DAY, DEFAULT_SEASON_END_DAY),
            ): _day_selector(),
            vol.Required(
                CONF_SEASON_REST_POSITION,
                default=defaults.get(CONF_SEASON_REST_POSITION, DEFAULT_SEASON_REST_POSITION),
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
