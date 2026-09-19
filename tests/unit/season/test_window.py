"""Tests for SeasonWindow: activity, pause periods and formatting."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.smart_venetian_blinds.const import (
    CONF_SEASON_END_DAY,
    CONF_SEASON_END_MONTH,
    CONF_SEASON_PAUSE_ENABLED,
    CONF_SEASON_REST_POSITION,
    CONF_SEASON_START_DAY,
    CONF_SEASON_START_MONTH,
)
from custom_components.smart_venetian_blinds.season import SeasonWindow, clamp_to_year

SUMMER = SeasonWindow(enabled=True, start_month=3, start_day=15, end_month=10, end_day=15)
WINTER = SeasonWindow(enabled=True, start_month=11, start_day=1, end_month=2, end_day=28)


@pytest.mark.unit
class TestSeasonWindowFromOptions:
    """Tests for SeasonWindow.from_options."""

    def test_defaults_when_options_empty(self) -> None:
        """Falls back to the default season when nothing is configured."""
        season = SeasonWindow.from_options({})

        assert season.enabled is False
        assert (season.start_month, season.start_day) == (3, 15)
        assert (season.end_month, season.end_day) == (10, 15)
        assert season.rest_position == 100

    def test_none_options(self) -> None:
        """Handles a missing options mapping."""
        assert SeasonWindow.from_options(None).enabled is False

    def test_reads_configured_values(self) -> None:
        """Reads all values from the options mapping."""
        season = SeasonWindow.from_options(
            {
                CONF_SEASON_PAUSE_ENABLED: True,
                CONF_SEASON_START_MONTH: 4,
                CONF_SEASON_START_DAY: 1,
                CONF_SEASON_END_MONTH: 9,
                CONF_SEASON_END_DAY: 30,
                CONF_SEASON_REST_POSITION: 80,
            }
        )

        assert season.enabled is True
        assert (season.start_month, season.start_day) == (4, 1)
        assert (season.end_month, season.end_day) == (9, 30)
        assert season.rest_position == 80

    def test_coerces_string_values(self) -> None:
        """Options that round-tripped through JSON as strings still parse."""
        season = SeasonWindow.from_options({CONF_SEASON_START_MONTH: "5", CONF_SEASON_END_MONTH: "8"})

        assert (season.start_month, season.end_month) == (5, 8)


@pytest.mark.unit
class TestSeasonWindowIsPaused:
    """Tests for the paused/active decision."""

    def test_disabled_never_pauses(self) -> None:
        """A disabled season never pauses, whatever the date."""
        assert SeasonWindow(enabled=False).is_paused(date(2026, 1, 1)) is False

    @pytest.mark.parametrize(
        ("today", "paused"),
        [
            (date(2026, 3, 14), True),  # day before season start
            (date(2026, 3, 15), False),  # start day is inclusive
            (date(2026, 7, 1), False),  # mid-season
            (date(2026, 10, 15), False),  # end day is inclusive
            (date(2026, 10, 16), True),  # first paused day
            (date(2026, 12, 31), True),  # deep in the pause
        ],
    )
    def test_normal_window(self, today: date, paused: bool) -> None:
        """Season from 15 March to 15 October, inclusive on both ends."""
        assert SUMMER.is_paused(today) is paused

    @pytest.mark.parametrize(
        ("today", "paused"),
        [
            (date(2026, 11, 1), False),  # start day
            (date(2026, 12, 24), False),  # after New Year's eve side
            (date(2026, 1, 15), False),  # before the end on the other side
            (date(2026, 2, 28), False),  # end day
            (date(2026, 3, 1), True),  # first paused day
            (date(2026, 10, 31), True),  # last paused day
        ],
    )
    def test_wrapping_window(self, today: date, paused: bool) -> None:
        """Season from 1 November to 28 February wraps across New Year."""
        assert WINTER.wraps_year_end is True
        assert WINTER.is_paused(today) is paused

    def test_single_day_window(self) -> None:
        """A season with identical start and end covers exactly one day."""
        season = SeasonWindow(enabled=True, start_month=6, start_day=21, end_month=6, end_day=21)

        assert season.is_paused(date(2026, 6, 21)) is False
        assert season.is_paused(date(2026, 6, 22)) is True


@pytest.mark.unit
class TestPausePeriodStart:
    """Tests for locating the pause period a date belongs to.

    The pause period is what makes the rest drive happen once per pause rather
    than once per configuration — it has to stay stable across New Year.
    """

    def test_none_while_active(self) -> None:
        """An active group is in no pause period."""
        assert SUMMER.pause_period_start(date(2026, 7, 1)) is None

    @pytest.mark.parametrize(
        "today",
        [date(2026, 10, 16), date(2026, 12, 31), date(2027, 1, 1), date(2027, 3, 14)],
    )
    def test_same_period_across_new_year(self, today: date) -> None:
        """Every day of one pause resolves to the same first paused day."""
        assert SUMMER.pause_period_start(today) == date(2026, 10, 16)

    def test_next_year_is_a_new_period(self) -> None:
        """The following pause is a distinct period, so the drive runs again."""
        assert SUMMER.pause_period_start(date(2027, 10, 20)) == date(2027, 10, 16)

    def test_wrapping_window_period(self) -> None:
        """A wrapping season has its pause inside a single calendar year."""
        assert WINTER.pause_period_start(date(2026, 3, 1)) == date(2026, 3, 1)
        assert WINTER.pause_period_start(date(2026, 10, 31)) == date(2026, 3, 1)

    def test_leap_day_end_in_common_year(self) -> None:
        """A 29 February end does not raise when the year has no leap day."""
        season = SeasonWindow(enabled=True, start_month=11, start_day=1, end_month=2, end_day=29)

        assert season.pause_period_start(date(2026, 6, 1)) == date(2026, 3, 1)


@pytest.mark.unit
class TestFormatting:
    """Tests for the human-readable and machine-readable renderings."""

    def test_identity_covers_window_and_rest_position(self) -> None:
        """Editing the rest position changes the identity, which re-arms the drive."""
        base = SeasonWindow(enabled=True, start_month=3, start_day=15, end_month=10, end_day=15, rest_position=100)
        moved = SeasonWindow(enabled=True, start_month=3, start_day=15, end_month=10, end_day=15, rest_position=0)
        later = SeasonWindow(enabled=True, start_month=4, start_day=1, end_month=10, end_day=15, rest_position=100)

        assert base.identity != moved.identity
        assert base.identity != later.identity

    def test_format_window_and_pause(self) -> None:
        """Both halves of the year are rendered for the options form."""
        assert SUMMER.format_window("en") == "15 March – 15 October"
        assert SUMMER.format_pause("en") == "16 October – 14 March"
        assert SUMMER.format_window("de") == "15. März – 15. Oktober"

    def test_format_pause_for_wrapping_window(self) -> None:
        """A wrapping season reports the paused months in between."""
        assert WINTER.format_pause("en") == "1 March – 31 October"

    def test_str_is_compact_for_logs(self) -> None:
        """The log representation stays stable and sortable."""
        assert str(SUMMER) == "03-15..10-15"

    def test_day_values(self) -> None:
        """Boundaries render as the MM-DD values the select stores."""
        assert (SUMMER.start_value, SUMMER.end_value) == ("03-15", "10-15")


@pytest.mark.unit
class TestClampToYear:
    """Tests for rendering a stored boundary in an arbitrary year."""

    def test_leap_day_in_common_year(self) -> None:
        """29 February clamps to 28 February when the year has no leap day."""
        assert clamp_to_year(2026, 2, 29) == date(2026, 2, 28)
        assert clamp_to_year(2024, 2, 29) == date(2024, 2, 29)

    def test_ordinary_date(self) -> None:
        """Anything else is passed through unchanged."""
        assert clamp_to_year(2026, 3, 15) == date(2026, 3, 15)
