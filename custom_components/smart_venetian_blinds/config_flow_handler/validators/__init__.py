"""
Validators for config flow inputs.

This package contains validation functions for user inputs across all flow types.
"""

from __future__ import annotations

from typing import Any

from custom_components.smart_venetian_blinds.const import (
    CONF_SEASON_END_DAY,
    CONF_SEASON_END_MONTH,
    CONF_SEASON_START_DAY,
    CONF_SEASON_START_MONTH,
)
from custom_components.smart_venetian_blinds.season import is_valid_month_day


def normalize_season_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """
    Coerce season month/day values to integers.

    The month dropdown submits strings and the day box submits floats; both are
    stored as plain integers so ``SeasonWindow`` can compare them directly.

    Args:
        user_input: Raw user input from the season options form.

    Returns:
        A copy of the input with month and day values as integers.
    """
    normalized = dict(user_input)
    for key in (CONF_SEASON_START_MONTH, CONF_SEASON_START_DAY, CONF_SEASON_END_MONTH, CONF_SEASON_END_DAY):
        if key in normalized:
            normalized[key] = int(float(normalized[key]))
    return normalized


def validate_season_input(user_input: dict[str, Any]) -> dict[str, str]:
    """
    Validate that both season boundaries are real calendar dates.

    Args:
        user_input: Normalized user input from the season options form.

    Returns:
        Mapping of field name to error key; empty when the input is valid.
    """
    errors: dict[str, str] = {}

    start_valid = is_valid_month_day(user_input[CONF_SEASON_START_MONTH], user_input[CONF_SEASON_START_DAY])
    if not start_valid:
        errors[CONF_SEASON_START_DAY] = "invalid_season_date"

    end_valid = is_valid_month_day(user_input[CONF_SEASON_END_MONTH], user_input[CONF_SEASON_END_DAY])
    if not end_valid:
        errors[CONF_SEASON_END_DAY] = "invalid_season_date"

    return errors


__all__: list[str] = [
    "normalize_season_input",
    "validate_season_input",
]
