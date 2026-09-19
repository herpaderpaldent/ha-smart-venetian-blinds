"""Tests for the persisted record of the one-time season rest drive."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from custom_components.smart_venetian_blinds.season import SeasonRestStore, SeasonWindow

COVER = "cover.living_room_blinds"
SUMMER = SeasonWindow(enabled=True, start_month=3, start_day=15, end_month=10, end_day=15)

FIRST_PAUSED_DAY = date(2026, 10, 16)
LATER_IN_PAUSE = date(2026, 12, 1)
NEXT_PAUSE = date(2027, 10, 20)


@pytest.fixture
def store() -> SeasonRestStore:
    """Return a store whose persistence layer is mocked out."""
    with patch("custom_components.smart_venetian_blinds.season.store.Store"):
        return SeasonRestStore(MagicMock(), "entry-1")


@pytest.mark.unit
class TestRestRecord:
    """Tests for the done/pending bookkeeping."""

    def test_nothing_recorded_initially(self, store: SeasonRestStore) -> None:
        """A cover starts with the drive outstanding."""
        assert store.is_done(COVER, SUMMER, FIRST_PAUSED_DAY) is False

    def test_marking_done_sticks_for_the_whole_pause(self, store: SeasonRestStore) -> None:
        """Once driven, the cover is left alone for the rest of the pause."""
        store.mark_done(COVER, SUMMER, FIRST_PAUSED_DAY)

        assert store.is_done(COVER, SUMMER, FIRST_PAUSED_DAY) is True
        assert store.is_done(COVER, SUMMER, LATER_IN_PAUSE) is True

    def test_next_year_re_arms_the_drive(self, store: SeasonRestStore) -> None:
        """A new pause period is a new drive — the record does not carry over."""
        store.mark_done(COVER, SUMMER, FIRST_PAUSED_DAY)

        assert store.is_done(COVER, SUMMER, NEXT_PAUSE) is False

    def test_changing_the_rest_position_re_arms_the_drive(self, store: SeasonRestStore) -> None:
        """Correcting the rest position mid-pause takes effect instead of being ignored."""
        store.mark_done(COVER, SUMMER, FIRST_PAUSED_DAY)
        corrected = SeasonWindow(enabled=True, start_month=3, start_day=15, end_month=10, end_day=15, rest_position=0)

        assert store.is_done(COVER, corrected, LATER_IN_PAUSE) is False

    def test_changing_the_season_re_arms_the_drive(self, store: SeasonRestStore) -> None:
        """Editing the window mid-pause also re-arms it."""
        store.mark_done(COVER, SUMMER, FIRST_PAUSED_DAY)
        moved = SeasonWindow(enabled=True, start_month=4, start_day=1, end_month=9, end_day=30)

        assert store.is_done(COVER, moved, LATER_IN_PAUSE) is False

    def test_other_covers_are_independent(self, store: SeasonRestStore) -> None:
        """A cover added during the pause still gets its own drive."""
        store.mark_done(COVER, SUMMER, FIRST_PAUSED_DAY)

        assert store.is_done("cover.new_one", SUMMER, LATER_IN_PAUSE) is False


@pytest.mark.unit
class TestPendingSince:
    """Tests for tracking how long the drive has been waiting."""

    def test_first_call_records_today(self, store: SeasonRestStore) -> None:
        """The first paused cycle starts the clock."""
        assert store.pending_since(COVER, SUMMER, FIRST_PAUSED_DAY) == FIRST_PAUSED_DAY

    def test_later_calls_keep_the_original_day(self, store: SeasonRestStore) -> None:
        """Waiting does not reset the clock, so the drive can expire."""
        store.pending_since(COVER, SUMMER, FIRST_PAUSED_DAY)

        assert store.pending_since(COVER, SUMMER, LATER_IN_PAUSE) == FIRST_PAUSED_DAY

    def test_a_new_pause_restarts_the_clock(self, store: SeasonRestStore) -> None:
        """Next year's pause gets its own grace day."""
        store.pending_since(COVER, SUMMER, FIRST_PAUSED_DAY)

        assert store.pending_since(COVER, SUMMER, NEXT_PAUSE) == NEXT_PAUSE


@pytest.mark.unit
class TestPersistence:
    """Tests for surviving a restart, which is the reason this store exists."""

    def test_records_survive_a_reload(self) -> None:
        """A restart mid-pause must neither re-drive nor cancel the drive."""
        saved: dict = {}

        with patch("custom_components.smart_venetian_blinds.season.store.Store") as store_cls:
            store_cls.return_value.async_delay_save.side_effect = lambda func, _delay: saved.update(func())
            first = SeasonRestStore(MagicMock(), "entry-1")
            first.mark_done(COVER, SUMMER, FIRST_PAUSED_DAY)

        assert saved, "the record must be scheduled for persistence"

        with patch("custom_components.smart_venetian_blinds.season.store.Store") as store_cls:
            store_cls.return_value.async_load = MagicMock(return_value=saved)
            restarted = SeasonRestStore(MagicMock(), "entry-1")
            restarted._data = dict(saved)  # noqa: SLF001 - stands in for the awaited async_load

        assert restarted.is_done(COVER, SUMMER, LATER_IN_PAUSE) is True

    def test_diagnostics_exposes_the_records(self, store: SeasonRestStore) -> None:
        """Support can see why a cover did or did not move."""
        store.mark_done(COVER, SUMMER, FIRST_PAUSED_DAY)

        assert COVER in store.as_diagnostics()
