"""
Cover subentry configuration schemas.

Schemas for configuring individual covers within a window group.
Split into multiple steps for a wizard-style configuration flow.
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
    CONF_MANUAL_OPEN_THRESHOLD,
    CONF_MAX_ANGLE,
    CONF_MIN_ANGLE,
    CONF_MIN_TILT_PERCENT,
    CONF_MINIMUM_TILT_CHANGE,
    CONF_OBSTACLE_ELEVATION_DEG,
    CONF_REFLECTION_PROTECTION_ENABLED,
    CONF_REFLECTION_PROTECTION_MIN_TILT,
    CONF_RESPECT_MANUAL_CLOSE,
    CONF_RESPECT_MANUAL_OPEN,
    DEFAULT_COVER_ENABLED,
    DEFAULT_DRIVE_POSITION,
    DEFAULT_INVERT_TILT,
    DEFAULT_MANUAL_CLOSE_THRESHOLD,
    DEFAULT_MANUAL_OPEN_THRESHOLD,
    DEFAULT_MAX_ANGLE,
    DEFAULT_MIN_ANGLE,
    DEFAULT_MIN_TILT_PERCENT,
    DEFAULT_MINIMUM_TILT_CHANGE,
    DEFAULT_OBSTACLE_ELEVATION_DEG,
    DEFAULT_REFLECTION_PROTECTION_ENABLED,
    DEFAULT_REFLECTION_PROTECTION_MIN_TILT,
    DEFAULT_RESPECT_MANUAL_CLOSE,
    DEFAULT_RESPECT_MANUAL_OPEN,
)
from homeassistant.helpers import selector


def get_cover_tilt_schema(
    defaults: Mapping[str, Any] | None = None,
    *,
    show_entity_selector: bool = True,
) -> vol.Schema:
    """
    Get schema for step 1: Cover entity and tilt settings.

    Args:
        defaults: Optional dictionary of default values to pre-populate the form.
        show_entity_selector: Whether to show the entity selector (false for reconfigure).

    Returns:
        Voluptuous schema for cover tilt configuration.
    """
    defaults = defaults or {}

    schema_dict: dict[Any, Any] = {}

    if not show_entity_selector:
        # Reconfigure mode: show enabled toggle at the top
        schema_dict[
            vol.Required(
                CONF_COVER_ENABLED,
                default=defaults.get(CONF_COVER_ENABLED, DEFAULT_COVER_ENABLED),
            )
        ] = selector.BooleanSelector()

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
                CONF_MINIMUM_TILT_CHANGE,
                default=defaults.get(CONF_MINIMUM_TILT_CHANGE, DEFAULT_MINIMUM_TILT_CHANGE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=20,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Required(
                CONF_MIN_TILT_PERCENT,
                default=defaults.get(CONF_MIN_TILT_PERCENT, DEFAULT_MIN_TILT_PERCENT),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Optional(
                CONF_OBSTACLE_ELEVATION_DEG,
                default=defaults.get(CONF_OBSTACLE_ELEVATION_DEG, DEFAULT_OBSTACLE_ELEVATION_DEG),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=90,
                    step=1,
                    unit_of_measurement="°",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        },
    )

    return vol.Schema(schema_dict)


def get_protection_schema(
    defaults: Mapping[str, Any] | None = None,
) -> vol.Schema:
    """
    Get schema for step 2: Protection options.

    Includes reflection protection and manual close settings.

    Args:
        defaults: Optional dictionary of default values to pre-populate the form.

    Returns:
        Voluptuous schema for protection configuration.
    """
    defaults = defaults or {}

    return vol.Schema(
        {
            vol.Required(
                CONF_REFLECTION_PROTECTION_ENABLED,
                default=defaults.get(
                    CONF_REFLECTION_PROTECTION_ENABLED,
                    DEFAULT_REFLECTION_PROTECTION_ENABLED,
                ),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_REFLECTION_PROTECTION_MIN_TILT,
                default=defaults.get(
                    CONF_REFLECTION_PROTECTION_MIN_TILT,
                    DEFAULT_REFLECTION_PROTECTION_MIN_TILT,
                ),
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
                CONF_RESPECT_MANUAL_OPEN,
                default=defaults.get(CONF_RESPECT_MANUAL_OPEN, DEFAULT_RESPECT_MANUAL_OPEN),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_MANUAL_OPEN_THRESHOLD,
                default=defaults.get(CONF_MANUAL_OPEN_THRESHOLD, DEFAULT_MANUAL_OPEN_THRESHOLD),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        }
    )


# Legacy function for backwards compatibility - not used in multi-step flow
def get_cover_subentry_schema(
    defaults: Mapping[str, Any] | None = None,
    *,
    show_entity_selector: bool = True,
) -> vol.Schema:
    """
    Get combined schema for cover subentry configuration.

    This is kept for backwards compatibility but is no longer used
    in the multi-step wizard flow.

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
                CONF_REFLECTION_PROTECTION_ENABLED,
                default=defaults.get(
                    CONF_REFLECTION_PROTECTION_ENABLED,
                    DEFAULT_REFLECTION_PROTECTION_ENABLED,
                ),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_REFLECTION_PROTECTION_MIN_TILT,
                default=defaults.get(
                    CONF_REFLECTION_PROTECTION_MIN_TILT,
                    DEFAULT_REFLECTION_PROTECTION_MIN_TILT,
                ),
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
                CONF_RESPECT_MANUAL_OPEN,
                default=defaults.get(CONF_RESPECT_MANUAL_OPEN, DEFAULT_RESPECT_MANUAL_OPEN),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_MANUAL_OPEN_THRESHOLD,
                default=defaults.get(CONF_MANUAL_OPEN_THRESHOLD, DEFAULT_MANUAL_OPEN_THRESHOLD),
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
                CONF_MINIMUM_TILT_CHANGE,
                default=defaults.get(CONF_MINIMUM_TILT_CHANGE, DEFAULT_MINIMUM_TILT_CHANGE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=20,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Required(
                CONF_MIN_TILT_PERCENT,
                default=defaults.get(CONF_MIN_TILT_PERCENT, DEFAULT_MIN_TILT_PERCENT),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Optional(
                CONF_OBSTACLE_ELEVATION_DEG,
                default=defaults.get(CONF_OBSTACLE_ELEVATION_DEG, DEFAULT_OBSTACLE_ELEVATION_DEG),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=90,
                    step=1,
                    unit_of_measurement="°",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
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
    "get_cover_tilt_schema",
    "get_protection_schema",
]
