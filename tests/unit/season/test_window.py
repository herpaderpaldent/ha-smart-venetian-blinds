"""Tests for SeasonWindow and season date validation."""

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
from custom_components.smart_venetian_blinds.season import SeasonWindow, is_valid_month_day


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

    def test_coerces_string_months(self) -> None:
        """Accepts the string values submitted by the month dropdown."""
        season = SeasonWindow.from_options(
            {
                CONF_SEASON_PAUSE_ENABLED: True,
                CONF_SEASON_START_MONTH: "5",
                CONF_SEASON_END_MONTH: "8",
            }
        )

        assert season.start_month == 5
        assert season.end_month == 8


@pytest.mark.unit
class TestSeasonWindowIsActive:
    """Tests for the active/paused decision."""

    def test_disabled_is_always_active(self) -> None:
        """A disabled season never pauses, whatever the date."""
        season = SeasonWindow(enabled=False, start_month=3, start_day=15, end_month=10, end_day=15)

        assert season.is_active(date(2026, 1, 1)) is True
        assert season.is_paused(date(2026, 1, 1)) is False

    @pytest.mark.parametrize(
        ("today", "expected_active"),
        [
            (date(2026, 3, 14), False),  # day before season start
            (date(2026, 3, 15), True),  # start day is inclusive
            (date(2026, 7, 1), True),  # mid-season
            (date(2026, 10, 15), True),  # end day is inclusive
            (date(2026, 10, 16), False),  # day after season end
            (date(2026, 12, 31), False),  # deep in the pause
        ],
    )
    def test_normal_window(self, today: date, expected_active: bool) -> None:
        """Season from 15 March to 15 October, inclusive on both ends."""
        season = SeasonWindow(enabled=True, start_month=3, start_day=15, end_month=10, end_day=15)

        assert season.is_active(today) is expected_active
        assert season.is_paused(today) is not expected_active

    @pytest.mark.parametrize(
        ("today", "expected_active"),
        [
            (date(2026, 11, 1), True),  # start day
            (date(2026, 12, 24), True),  # after New Year's eve side
            (date(2026, 1, 15), True),  # before the end on the other side
            (date(2026, 2, 28), True),  # end day
            (date(2026, 3, 1), False),  # just outside
            (date(2026, 10, 31), False),  # just before the start
        ],
    )
    def test_wrapping_window(self, today: date, expected_active: bool) -> None:
        """Season from 01 November to 28 February wraps across New Year."""
        season = SeasonWindow(enabled=True, start_month=11, start_day=1, end_month=2, end_day=28)

        assert season.wraps_year_end is True
        assert season.is_active(today) is expected_active

    def test_single_day_window(self) -> None:
        """A season with identical start and end covers exactly one day."""
        season = SeasonWindow(enabled=True, start_month=6, start_day=21, end_month=6, end_day=21)

        assert season.is_active(date(2026, 6, 21)) is True
        assert season.is_active(date(2026, 6, 22)) is False

    def test_leap_day_inside_wrapping_window(self) -> None:
        """29 February falls inside a window ending on 29 February."""
        season = SeasonWindow(enabled=True, start_month=11, start_day=1, end_month=2, end_day=29)

        assert season.is_active(date(2024, 2, 29)) is True

    def test_describe(self) -> None:
        """describe() renders a zero-padded dd.mm-dd.mm window."""
        season = SeasonWindow(enabled=True, start_month=3, start_day=1, end_month=10, end_day=15)

        assert season.describe() == "01.03-15.10"


@pytest.mark.unit
class TestIsValidMonthDay:
    """Tests for calendar date validation."""

    @pytest.mark.parametrize(
        ("month", "day", "expected"),
        [
            (1, 31, True),
            (2, 29, True),  # leap day stays configurable
            (2, 30, False),
            (4, 30, True),
            (4, 31, False),
            (12, 31, True),
            (0, 1, False),
            (13, 1, False),
            (6, 0, False),
        ],
    )
    def test_validation(self, month: int, day: int, expected: bool) -> None:
        """Only real calendar dates are accepted."""
        assert is_valid_month_day(month, day) is expected
