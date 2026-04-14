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
    DEFAULT_CHANGE_THRESHOLD,
    DEFAULT_MIN_UPDATE_INTERVAL,
    DEFAULT_POSITION_SETTLING_DELAY,
    DEFAULT_POSITION_TIMEOUT,
)
from homeassistant.helpers import selector


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
]
