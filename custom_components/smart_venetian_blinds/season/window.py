"""
Seasonal activity window for a window group.

A window group can be restricted to a recurring part of the year (e.g. 15 March
to 15 October). Outside that window the control pipeline stops driving covers —
see ``SeasonalPausePipe``. The window is year-agnostic: only (month, day) is
compared, so it repeats every year without reconfiguration.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import (
    CONF_SEASON_END_DAY,
    CONF_SEASON_END_MONTH,
    CONF_SEASON_PAUSE_ENABLED,
    CONF_SEASON_REST_POSITION,
    CONF_SEASON_START_DAY,
    CONF_SEASON_START_MONTH,
    DEFAULT_SEASON_END_DAY,
    DEFAULT_SEASON_END_MONTH,
    DEFAULT_SEASON_PAUSE_ENABLED,
    DEFAULT_SEASON_REST_POSITION,
    DEFAULT_SEASON_START_DAY,
    DEFAULT_SEASON_START_MONTH,
)
from custom_components.smart_venetian_blinds.season.day_options import format_day, to_day_value

# A common year: the paused range is described the way it reads in three years out
# of four. In a leap year a pause after a 28 February end really does start a day
# earlier, which is a boundary detail no summary line should hinge on.
_DESCRIPTION_YEAR = 2025

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any


def clamp_to_year(year: int, month: int, day: int) -> date:
    """
    Build a date, moving 29 February to 28 February in a common year.

    A leap-day boundary stays configurable, so it has to remain renderable in
    every year without raising.

    Args:
        year: The year to build the date in.
        month: The stored month.
        day: The stored day of month.

    Returns:
        A valid date in the given year.
    """
    if month == 2 and day == 29 and not calendar.isleap(year):
        return date(year, 2, 28)
    return date(year, month, day)


@dataclass(frozen=True)
class SeasonWindow:
    """
    Recurring yearly window during which the group actively controls covers.

    The window is inclusive on both ends and wraps across New Year when the start
    date is after the end date (e.g. 01 November to 28 February).
    """

    enabled: bool = DEFAULT_SEASON_PAUSE_ENABLED
    start_month: int = DEFAULT_SEASON_START_MONTH
    start_day: int = DEFAULT_SEASON_START_DAY
    end_month: int = DEFAULT_SEASON_END_MONTH
    end_day: int = DEFAULT_SEASON_END_DAY
    rest_position: int = DEFAULT_SEASON_REST_POSITION

    @classmethod
    def from_options(cls, options: Mapping[str, Any] | None) -> SeasonWindow:
        """Create a SeasonWindow from a config entry's options mapping."""
        options = options or {}
        return cls(
            enabled=bool(options.get(CONF_SEASON_PAUSE_ENABLED, DEFAULT_SEASON_PAUSE_ENABLED)),
            start_month=int(options.get(CONF_SEASON_START_MONTH, DEFAULT_SEASON_START_MONTH)),
            start_day=int(options.get(CONF_SEASON_START_DAY, DEFAULT_SEASON_START_DAY)),
            end_month=int(options.get(CONF_SEASON_END_MONTH, DEFAULT_SEASON_END_MONTH)),
            end_day=int(options.get(CONF_SEASON_END_DAY, DEFAULT_SEASON_END_DAY)),
            rest_position=int(options.get(CONF_SEASON_REST_POSITION, DEFAULT_SEASON_REST_POSITION)),
        )

    @property
    def wraps_year_end(self) -> bool:
        """Return True if the active window spans New Year (start after end)."""
        return (self.start_month, self.start_day) > (self.end_month, self.end_day)

    @property
    def start_value(self) -> str:
        """Return the season start as a ``MM-DD`` option value."""
        return to_day_value(self.start_month, self.start_day)

    @property
    def end_value(self) -> str:
        """Return the season end as a ``MM-DD`` option value."""
        return to_day_value(self.end_month, self.end_day)

    @property
    def identity(self) -> str:
        """
        Return a token identifying this window and its rest position.

        A stored "rest drive already done" record is discarded when this token
        changes, so editing the season or the rest position during a pause takes
        effect instead of being silently ignored.
        """
        return f"{self.start_value}:{self.end_value}@{self.rest_position}"

    def is_paused(self, today: date) -> bool:
        """Return True if the group is seasonally paused on the given date."""
        if not self.enabled:
            return False

        current = (today.month, today.day)
        start = (self.start_month, self.start_day)
        end = (self.end_month, self.end_day)

        if self.wraps_year_end:
            active = current >= start or current <= end
        else:
            active = start <= current <= end
        return not active

    def pause_period_start(self, today: date) -> date | None:
        """
        Return the first day of the pause period containing ``today``.

        The pause runs from the day after the season ends until the day before it
        starts again. Used to tell one year's pause from the next, so the one-time
        rest drive happens once per pause rather than once per configuration.

        Args:
            today: The date to locate.

        Returns:
            The first paused day, or None if the group is active on ``today``.
        """
        if not self.is_paused(today):
            return None

        candidate = clamp_to_year(today.year, self.end_month, self.end_day) + timedelta(days=1)
        if candidate > today:
            candidate = clamp_to_year(today.year - 1, self.end_month, self.end_day) + timedelta(days=1)
        return candidate

    def format_window(self, language: str | None = None) -> str:
        """Return the active window for humans, e.g. ``15 March – 15 October``."""
        start = format_day(self.start_month, self.start_day, language)
        end = format_day(self.end_month, self.end_day, language)
        return f"{start} – {end}"

    def format_pause(self, language: str | None = None) -> str:
        """Return the paused part of the year for humans."""
        after_end = clamp_to_year(_DESCRIPTION_YEAR, self.end_month, self.end_day) + timedelta(days=1)
        before_start = clamp_to_year(_DESCRIPTION_YEAR, self.start_month, self.start_day) - timedelta(days=1)
        start = format_day(after_end.month, after_end.day, language)
        end = format_day(before_start.month, before_start.day, language)
        return f"{start} – {end}"

    def __str__(self) -> str:
        """Return a compact representation for logs and diagnostics."""
        return f"{self.start_value}..{self.end_value}"


__all__ = [
    "SeasonWindow",
    "clamp_to_year",
]
