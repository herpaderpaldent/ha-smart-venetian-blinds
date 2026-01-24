"""
Cover subentry configuration schemas.

Schemas for configuring individual covers within a window group.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.smart_venetian_blinds.const import (
    CONF_COVER_ENABLED,
    CONF_COVER_ENTITY,
    CONF_COVER_NAME,
    CONF_DRIVE_POSITION,
    CONF_INVERT_TILT,
    CONF_MANUAL_CLOSE_THRESHOLD,
    CONF_MAX_ANGLE,
    CONF_MIN_ANGLE,
    CONF_NO_SUN_BEHAVIOR,
    CONF_NO_SUN_POSITION,
    CONF_RESPECT_MANUAL_CLOSE,
    CONF_TILT_ONLY_WHEN_DRIVEN,
    DEFAULT_COVER_ENABLED,
    DEFAULT_DRIVE_POSITION,
    DEFAULT_INVERT_TILT,
    DEFAULT_MANUAL_CLOSE_THRESHOLD,
    DEFAULT_MAX_ANGLE,
    DEFAULT_MIN_ANGLE,
    DEFAULT_NO_SUN_BEHAVIOR,
    DEFAULT_NO_SUN_POSITION,
    DEFAULT_RESPECT_MANUAL_CLOSE,
    DEFAULT_TILT_ONLY_WHEN_DRIVEN,
)
from homeassistant.helpers import selector

NO_SUN_BEHAVIOR_OPTIONS = [
    selector.SelectOptionDict(value="keep_last", label="Keep last position"),
    selector.SelectOptionDict(value="open", label="Fully open"),
    selector.SelectOptionDict(value="close", label="Fully close"),
    selector.SelectOptionDict(value="set_to_percent", label="Set to specific percent"),
]


def get_cover_subentry_schema(
    defaults: Mapping[str, Any] | None = None,
    *,
    show_entity_selector: bool = True,
) -> vol.Schema:
    """
    Get schema for cover subentry configuration.

    Args:
        defaults: Optional dictionary of default values to pre-populate the form.
        show_entity_selector: Whether to show the entity selector (false for reconfigure).

    Returns:
        Voluptuous schema for cover configuration.
    """
    defaults = defaults or {}

    schema_dict: dict[Any, Any] = {}

    if show_entity_selector:
        schema_dict[vol.Required(CONF_COVER_ENTITY)] = selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="cover",
                multiple=False,
            ),
        )

    schema_dict.update(
        {
            vol.Optional(
                CONF_COVER_NAME,
                default=defaults.get(CONF_COVER_NAME, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                ),
            ),
            vol.Required(
                CONF_DRIVE_POSITION,
                default=defaults.get(CONF_DRIVE_POSITION, DEFAULT_DRIVE_POSITION),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Required(
                CONF_MIN_ANGLE,
                default=defaults.get(CONF_MIN_ANGLE, DEFAULT_MIN_ANGLE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-90,
                    max=90,
                    step=1,
                    unit_of_measurement="°",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_MAX_ANGLE,
                default=defaults.get(CONF_MAX_ANGLE, DEFAULT_MAX_ANGLE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-90,
                    max=90,
                    step=1,
                    unit_of_measurement="°",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_INVERT_TILT,
                default=defaults.get(CONF_INVERT_TILT, DEFAULT_INVERT_TILT),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_NO_SUN_BEHAVIOR,
                default=defaults.get(CONF_NO_SUN_BEHAVIOR, DEFAULT_NO_SUN_BEHAVIOR),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=NO_SUN_BEHAVIOR_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="no_sun_behavior",
                ),
            ),
            vol.Optional(
                CONF_NO_SUN_POSITION,
                default=defaults.get(CONF_NO_SUN_POSITION, DEFAULT_NO_SUN_POSITION),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Required(
                CONF_RESPECT_MANUAL_CLOSE,
                default=defaults.get(CONF_RESPECT_MANUAL_CLOSE, DEFAULT_RESPECT_MANUAL_CLOSE),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_MANUAL_CLOSE_THRESHOLD,
                default=defaults.get(CONF_MANUAL_CLOSE_THRESHOLD, DEFAULT_MANUAL_CLOSE_THRESHOLD),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Required(
                CONF_TILT_ONLY_WHEN_DRIVEN,
                default=defaults.get(CONF_TILT_ONLY_WHEN_DRIVEN, DEFAULT_TILT_ONLY_WHEN_DRIVEN),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_COVER_ENABLED,
                default=defaults.get(CONF_COVER_ENABLED, DEFAULT_COVER_ENABLED),
            ): selector.BooleanSelector(),
        },
    )

    return vol.Schema(schema_dict)


def get_cover_reconfigure_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """
    Get schema for reconfiguring a cover subentry.

    Args:
        defaults: Current configuration values.

    Returns:
        Voluptuous schema for cover reconfiguration.
    """
    return get_cover_subentry_schema(defaults, show_entity_selector=False)


__all__ = [
    "get_cover_reconfigure_schema",
    "get_cover_subentry_schema",
]
