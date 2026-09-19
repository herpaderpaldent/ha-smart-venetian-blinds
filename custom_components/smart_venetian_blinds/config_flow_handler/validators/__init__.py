"""
Validators for config flow inputs.

This package contains validation functions for user inputs across all flow types.
"""

from __future__ import annotations

from typing import Any

from custom_components.smart_venetian_blinds.const import (
    CONF_SEASON_END,
    CONF_SEASON_END_DAY,
    CONF_SEASON_END_MONTH,
    CONF_SEASON_START,
    CONF_SEASON_START_DAY,
    CONF_SEASON_START_MONTH,
)
from custom_components.smart_venetian_blinds.season import parse_day_value

_SEASON_DAY_FIELDS = (
    (CONF_SEASON_START, CONF_SEASON_START_MONTH, CONF_SEASON_START_DAY),
    (CONF_SEASON_END, CONF_SEASON_END_MONTH, CONF_SEASON_END_DAY),
)


def normalize_season_input(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Convert the season day dropdowns into the stored month/day values.

    The form offers a ``MM-DD`` value per boundary because Home Assistant has no
    month/day selector; only month and day are stored, so the season repeats every
    year. A value the dropdown cannot have produced is reported rather than stored.

    Args:
        user_input: Raw user input from the season options form.

    Returns:
        The normalized input, and a mapping of field name to error key which is
        empty when everything parsed.
    """
    normalized = dict(user_input)
    errors: dict[str, str] = {}

    for field, month_key, day_key in _SEASON_DAY_FIELDS:
        if field not in normalized:
            continue
        try:
            month, day = parse_day_value(normalized[field])
        except (ValueError, TypeError):
            errors[field] = "invalid_season_date"
            continue
        normalized.pop(field)
        normalized[month_key] = month
        normalized[day_key] = day

    return normalized, errors


__all__: list[str] = [
    "normalize_season_input",
]
