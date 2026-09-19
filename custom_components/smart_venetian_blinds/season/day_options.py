"""
Day-of-year option values for the season boundaries.

Home Assistant has no month/day selector and no month/day entity, so both the
options flow and the device page offer a list of all 366 possible boundaries.
The stored value is a language-independent ``MM-DD`` string; only the label
shown to the user is localized.
"""

from __future__ import annotations

from datetime import date, timedelta

DEFAULT_LANGUAGE = "en"

MONTH_NAMES: dict[str, tuple[str, ...]] = {
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "de": (
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ),
}

# A leap year, so 29 February is offered like any other day.
_OPTION_YEAR = 2024


def normalize_language(language: str | None) -> str:
    """
    Reduce a Home Assistant language tag to one this module has month names for.

    Args:
        language: A language tag such as ``de`` or ``de-CH``, or None.

    Returns:
        A key of ``MONTH_NAMES``; falls back to English.
    """
    if not language:
        return DEFAULT_LANGUAGE
    base = language.replace("_", "-").split("-")[0].lower()
    return base if base in MONTH_NAMES else DEFAULT_LANGUAGE


def to_day_value(month: int, day: int) -> str:
    """Return the stored ``MM-DD`` value for a month and day."""
    return f"{month:02d}-{day:02d}"


def parse_day_value(value: str) -> tuple[int, int]:
    """
    Parse a ``MM-DD`` value into month and day.

    Args:
        value: A ``MM-DD`` string.

    Returns:
        The month and day as integers.

    Raises:
        ValueError: If the value is not a real ``MM-DD`` boundary.
    """
    month_text, _, day_text = str(value).partition("-")
    month, day = int(month_text), int(day_text)
    # Round-trip through a leap year so impossible dates such as 02-30 are rejected.
    date(_OPTION_YEAR, month, day)
    return month, day


def format_day(month: int, day: int, language: str | None = None) -> str:
    """
    Render a boundary for humans, e.g. ``15 March`` or ``15. März``.

    Args:
        month: The month.
        day: The day of month.
        language: Home Assistant's configured language.

    Returns:
        A localized label.
    """
    lang = normalize_language(language)
    month_name = MONTH_NAMES[lang][month - 1]
    if lang == "de":
        return f"{day}. {month_name}"
    return f"{day} {month_name}"


def day_choices(language: str | None = None) -> list[tuple[str, str]]:
    """
    Return every possible boundary as ``(value, label)``, ordered by calendar date.

    Args:
        language: Home Assistant's configured language.

    Returns:
        366 ``(MM-DD, label)`` pairs, including 29 February.
    """
    choices: list[tuple[str, str]] = []
    current = date(_OPTION_YEAR, 1, 1)
    end = date(_OPTION_YEAR, 12, 31)
    while current <= end:
        choices.append((to_day_value(current.month, current.day), format_day(current.month, current.day, language)))
        current += timedelta(days=1)
    return choices


__all__ = [
    "DEFAULT_LANGUAGE",
    "MONTH_NAMES",
    "day_choices",
    "format_day",
    "normalize_language",
    "parse_day_value",
    "to_day_value",
]
