"""Tests for config entry setup helpers."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.smart_venetian_blinds import (
    SEASON_REST_STORE_KEY,
    _restore_season_rest_flags,
    _season_rest_store,
)
from custom_components.smart_venetian_blinds.const import (
    CONF_COVER_ENTITY,
    CONF_SEASON_END_DAY,
    CONF_SEASON_END_MONTH,
    CONF_SEASON_PAUSE_ENABLED,
    CONF_SEASON_START_DAY,
    CONF_SEASON_START_MONTH,
    DOMAIN,
)
from custom_components.smart_venetian_blinds.coordinator.state import GroupState
from custom_components.smart_venetian_blinds.cover_control.context import CoverTrackingState

COVER = "cover.living_room_blinds"

SEASON_OPTIONS = {
    CONF_SEASON_PAUSE_ENABLED: True,
    CONF_SEASON_START_MONTH: 3,
    CONF_SEASON_START_DAY: 15,
    CONF_SEASON_END_MONTH: 10,
    CONF_SEASON_END_DAY: 15,
}

IN_SEASON = datetime(2026, 7, 1, 12, 0)
PAUSED = datetime(2026, 11, 1, 12, 0)


def _patch_now(moment: datetime) -> object:
    """Patch the setup module's clock to a fixed moment."""
    return patch("custom_components.smart_venetian_blinds.dt_util.now", return_value=moment)


def _make_entry(options: dict | None = None) -> MagicMock:
    """Build a mock config entry with one cover subentry."""
    subentry = MagicMock()
    subentry.data = {CONF_COVER_ENTITY: COVER}

    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.title = "South Windows"
    entry.options = options if options is not None else dict(SEASON_OPTIONS)
    entry.subentries = {"sub-1": subentry}
    entry.runtime_data.state = GroupState()
    return entry


@pytest.mark.unit
class TestRestoreSeasonRestFlags:
    """Tests for seeding season_rest_applied at entry setup."""

    def test_in_season_leaves_state_untouched(self) -> None:
        """Inside the season no cover state is created."""
        hass = MagicMock()
        hass.data = {}
        entry = _make_entry()

        with _patch_now(IN_SEASON):
            _restore_season_rest_flags(hass, entry)

        assert entry.runtime_data.state.cover_states == {}

    def test_disabled_pause_leaves_state_untouched(self) -> None:
        """A disabled seasonal pause never seeds flags."""
        hass = MagicMock()
        hass.data = {}
        entry = _make_entry({**SEASON_OPTIONS, CONF_SEASON_PAUSE_ENABLED: False})

        with _patch_now(PAUSED):
            _restore_season_rest_flags(hass, entry)

        assert entry.runtime_data.state.cover_states == {}

    def test_fresh_start_while_paused_marks_rest_applied(self) -> None:
        """A restart during the pause must not move covers again."""
        hass = MagicMock()
        hass.data = {}
        entry = _make_entry()

        with _patch_now(PAUSED):
            _restore_season_rest_flags(hass, entry)

        assert entry.runtime_data.state.cover_states[COVER].season_rest_applied is True

    def test_reload_keeps_previous_flags(self) -> None:
        """A reload during the pause carries the stored flags over."""
        hass = MagicMock()
        hass.data = {DOMAIN: {SEASON_REST_STORE_KEY: {"entry-1": {COVER: False}}}}
        entry = _make_entry()

        with _patch_now(PAUSED):
            _restore_season_rest_flags(hass, entry)

        # Pause was enabled during this HA run: the one-time rest drive is still pending.
        assert entry.runtime_data.state.cover_states[COVER].season_rest_applied is False

    def test_reload_marks_cover_added_during_pause(self) -> None:
        """A cover unknown to the stored flags still gets its rest drive."""
        hass = MagicMock()
        hass.data = {DOMAIN: {SEASON_REST_STORE_KEY: {"entry-1": {"cover.other": True}}}}
        entry = _make_entry()

        with _patch_now(PAUSED):
            _restore_season_rest_flags(hass, entry)

        assert entry.runtime_data.state.cover_states[COVER].season_rest_applied is False

    def test_existing_cover_state_is_preserved(self) -> None:
        """Seeding updates the season flag without discarding other tracking state."""
        hass = MagicMock()
        hass.data = {}
        entry = _make_entry()
        entry.runtime_data.state.cover_states[COVER] = CoverTrackingState(in_no_sun=True)

        with _patch_now(PAUSED):
            _restore_season_rest_flags(hass, entry)

        cover_state = entry.runtime_data.state.cover_states[COVER]
        assert cover_state.season_rest_applied is True
        assert cover_state.in_no_sun is True


@pytest.mark.unit
class TestSeasonRestStore:
    """Tests for the hass.data store helper."""

    def test_creates_nested_structure(self) -> None:
        """The store is created under the integration's hass.data key."""
        hass = MagicMock()
        hass.data = {}

        store = _season_rest_store(hass)
        store["entry-1"] = {COVER: True}

        assert hass.data[DOMAIN][SEASON_REST_STORE_KEY]["entry-1"] == {COVER: True}
