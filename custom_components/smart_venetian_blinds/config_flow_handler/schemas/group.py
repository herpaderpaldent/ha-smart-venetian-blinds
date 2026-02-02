"""
Group configuration schemas.

Schemas for configuring a window group (facade orientation + slat geometry).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.smart_venetian_blinds.const import (
    CONF_FACADE_AZIMUTH,
    CONF_GROUP_NAME,
    CONF_SAFETY_MARGIN,
    CONF_SLAT_SPACING,
    CONF_SLAT_WIDTH,
    DEFAULT_FACADE_AZIMUTH,
    DEFAULT_SAFETY_MARGIN,
    DEFAULT_SLAT_SPACING,
    DEFAULT_SLAT_WIDTH,
)
from homeassistant.helpers import selector


def get_group_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """
    Get schema for window group configuration.

    Args:
        defaults: Optional dictionary of default values to pre-populate the form.

    Returns:
        Voluptuous schema for group configuration.
    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_GROUP_NAME,
                default=defaults.get(CONF_GROUP_NAME, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                ),
            ),
            vol.Required(
                CONF_FACADE_AZIMUTH,
                default=defaults.get(CONF_FACADE_AZIMUTH, DEFAULT_FACADE_AZIMUTH),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=359,
                    step=1,
                    unit_of_measurement="°",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Required(
                CONF_SLAT_WIDTH,
                default=defaults.get(CONF_SLAT_WIDTH, DEFAULT_SLAT_WIDTH),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=200,
                    step=1,
                    unit_of_measurement="mm",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_SLAT_SPACING,
                default=defaults.get(CONF_SLAT_SPACING, DEFAULT_SLAT_SPACING),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=200,
                    step=1,
                    unit_of_measurement="mm",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_SAFETY_MARGIN,
                default=defaults.get(CONF_SAFETY_MARGIN, DEFAULT_SAFETY_MARGIN),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=15,
                    step=0.5,
                    unit_of_measurement="°",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        },
    )


def get_group_reconfigure_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """
    Get schema for reconfiguring a window group.

    Args:
        defaults: Current configuration values.

    Returns:
        Voluptuous schema for group reconfiguration.
    """
    return vol.Schema(
        {
            vol.Required(
                CONF_FACADE_AZIMUTH,
                default=defaults.get(CONF_FACADE_AZIMUTH, DEFAULT_FACADE_AZIMUTH),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=359,
                    step=1,
                    unit_of_measurement="°",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Required(
                CONF_SLAT_WIDTH,
                default=defaults.get(CONF_SLAT_WIDTH, DEFAULT_SLAT_WIDTH),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=200,
                    step=1,
                    unit_of_measurement="mm",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_SLAT_SPACING,
                default=defaults.get(CONF_SLAT_SPACING, DEFAULT_SLAT_SPACING),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=200,
                    step=1,
                    unit_of_measurement="mm",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_SAFETY_MARGIN,
                default=defaults.get(CONF_SAFETY_MARGIN, DEFAULT_SAFETY_MARGIN),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=15,
                    step=0.5,
                    unit_of_measurement="°",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        },
    )


__all__ = [
    "get_group_reconfigure_schema",
    "get_group_schema",
]
