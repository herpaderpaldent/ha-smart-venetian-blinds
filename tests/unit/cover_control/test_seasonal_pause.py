"""Tests for SeasonalPausePipe, exercised through the real cover control pipeline."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.smart_venetian_blinds.cover_control.controller import CoverController
from custom_components.smart_venetian_blinds.season import SeasonRestStore, SeasonWindow
from tests.conftest import create_mock_state

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.cover_control.controller import CoverConfig
    from custom_components.smart_venetian_blinds.sun.math import SlatCalculationResult

SEASON = SeasonWindow(enabled=True, start_month=3, start_day=15, end_month=10, end_day=15, rest_position=100)

IN_SEASON_NOON = datetime(2026, 7, 1, 12, 0)
FIRST_PAUSED_DAY_NIGHT = datetime(2026, 10, 16, 0, 2)
FIRST_PAUSED_DAY_NOON = datetime(2026, 10, 16, 12, 0)
SECOND_PAUSED_DAY_NOON = datetime(2026, 10, 17, 12, 0)
SEASON_RESUMES_NIGHT = datetime(2027, 3, 15, 0, 2)


def _patch_now(moment: datetime) -> object:
    """Patch the clock the pipe reads."""
    return patch(
        "custom_components.smart_venetian_blinds.cover_control.pipes.seasonal_pause.dt_util.now",
        return_value=moment,
    )


@pytest.fixture
def store() -> SeasonRestStore:
    """Return a rest store with persistence mocked out."""
    with patch("custom_components.smart_venetian_blinds.season.store.Store"):
        return SeasonRestStore(MagicMock(), "entry-1")


def _controller(hass: MagicMock, store: SeasonRestStore, season: SeasonWindow = SEASON) -> CoverController:
    """Build a controller running the real pipeline."""
    return CoverController(hass, position_timeout_sec=1, settling_delay_sec=0, season=season, season_store=store)


def _cover_state(position: int = 20, tilt: int = 50) -> MagicMock:
    """Return a cover state that is neither driving nor manually closed."""
    return create_mock_state(attributes={"current_position": position, "current_tilt_position": tilt})


@pytest.mark.unit
class TestInSeason:
    """The pipe must stay out of the way while the group is active."""

    async def test_pipeline_continues_to_tilt(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """In season the calculated tilt is applied as usual."""
        mock_hass.states.get.return_value = _cover_state(position=50, tilt=40)
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(IN_SEASON_NOON):
            applied = await _controller(mock_hass, store).apply_calculation(
                cover_config_default, calculation_result_direct_sun
            )

        assert applied is True
        services = [call[0][1] for call in mock_hass.services.async_call.await_args_list]
        assert "set_cover_tilt_position" in services

    async def test_disabled_season_never_pauses(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """With the seasonal schedule off, an out-of-season date changes nothing."""
        mock_hass.states.get.return_value = _cover_state(position=50, tilt=40)
        mock_hass.services.async_call = AsyncMock()
        controller = _controller(mock_hass, store, SeasonWindow(enabled=False))

        with _patch_now(FIRST_PAUSED_DAY_NOON):
            await controller.apply_calculation(cover_config_default, calculation_result_direct_sun)

        services = [call[0][1] for call in mock_hass.services.async_call.await_args_list]
        assert "set_cover_tilt_position" in services


@pytest.mark.unit
class TestPauseBegins:
    """The one-time rest drive."""

    async def test_no_movement_at_night(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
    ) -> None:
        """The pause must never raise a cover in the dark."""
        mock_hass.states.get.return_value = _cover_state()
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(FIRST_PAUSED_DAY_NIGHT):
            applied = await _controller(mock_hass, store).apply_calculation(cover_config_default, None)

        assert applied is False
        mock_hass.services.async_call.assert_not_awaited()
        assert store.is_done(cover_config_default.entity_id, SEASON, date(2026, 10, 16)) is False

    async def test_drives_to_rest_position_in_daylight(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """The first sunlit cycle parks the cover at the rest position."""
        mock_hass.states.get.return_value = _cover_state(position=20)
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(FIRST_PAUSED_DAY_NOON):
            applied = await _controller(mock_hass, store).apply_calculation(
                cover_config_default, calculation_result_direct_sun
            )

        assert applied is True
        call = mock_hass.services.async_call.await_args_list[0]
        assert call[0][1] == "set_cover_position"
        assert call[0][2]["position"] == 100
        assert store.is_done(cover_config_default.entity_id, SEASON, date(2026, 10, 16)) is True

    async def test_only_once(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """A cover moved by hand afterwards is left where the user put it."""
        mock_hass.states.get.return_value = _cover_state(position=20)
        mock_hass.services.async_call = AsyncMock()
        controller = _controller(mock_hass, store)

        with _patch_now(FIRST_PAUSED_DAY_NOON):
            await controller.apply_calculation(cover_config_default, calculation_result_direct_sun)
        mock_hass.services.async_call.reset_mock()
        mock_hass.states.get.return_value = _cover_state(position=70)

        with _patch_now(SECOND_PAUSED_DAY_NOON):
            applied = await controller.apply_calculation(cover_config_default, calculation_result_direct_sun)

        assert applied is False
        mock_hass.services.async_call.assert_not_awaited()

    async def test_manually_closed_cover_is_not_disturbed(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Closed slats outrank the rest drive, even though the pipe runs first."""
        mock_hass.states.get.return_value = _cover_state(position=20, tilt=0)
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(FIRST_PAUSED_DAY_NOON):
            applied = await _controller(mock_hass, store).apply_calculation(
                cover_config_default, calculation_result_direct_sun
            )

        assert applied is False
        mock_hass.services.async_call.assert_not_awaited()

    async def test_blocked_drive_expires_instead_of_firing_weeks_later(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """A drive that missed its day is abandoned, not left armed."""
        mock_hass.states.get.return_value = _cover_state(position=20, tilt=0)
        mock_hass.services.async_call = AsyncMock()
        controller = _controller(mock_hass, store)

        with _patch_now(FIRST_PAUSED_DAY_NOON):
            await controller.apply_calculation(cover_config_default, calculation_result_direct_sun)

        # Next day the user opens the slats — nothing may lurch into motion.
        mock_hass.states.get.return_value = _cover_state(position=20, tilt=60)
        with _patch_now(SECOND_PAUSED_DAY_NOON):
            applied = await controller.apply_calculation(cover_config_default, calculation_result_direct_sun)

        assert applied is False
        mock_hass.services.async_call.assert_not_awaited()
        assert store.is_done(cover_config_default.entity_id, SEASON, date(2026, 10, 17)) is True

    async def test_already_at_rest_position_issues_no_command(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """A cover already parked is recorded as done without moving."""
        mock_hass.states.get.return_value = _cover_state(position=99)
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(FIRST_PAUSED_DAY_NOON):
            applied = await _controller(mock_hass, store).apply_calculation(
                cover_config_default, calculation_result_direct_sun
            )

        assert applied is False
        mock_hass.services.async_call.assert_not_awaited()
        assert store.is_done(cover_config_default.entity_id, SEASON, date(2026, 10, 16)) is True


@pytest.mark.unit
class TestSeasonResumes:
    """The transition back into the season, which used to move covers at night."""

    async def test_nothing_moves_when_the_season_starts_at_midnight(
        self,
        cover_config_no_sun_open: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
    ) -> None:
        """Resuming must not look like a fresh no-sun period to NoSunPipe."""
        mock_hass.states.get.return_value = _cover_state(position=100)
        mock_hass.services.async_call = AsyncMock()
        controller = _controller(mock_hass, store)

        # Park the cover during the pause, then keep cycling through the pause the way
        # sun events really do — including at night — before the season comes back.
        with _patch_now(FIRST_PAUSED_DAY_NOON):
            await controller.apply_calculation(cover_config_no_sun_open, MagicMock(sun_is_behind_facade=False))
        with _patch_now(datetime(2027, 3, 14, 23, 40)):
            await controller.apply_calculation(cover_config_no_sun_open, None)
        mock_hass.services.async_call.reset_mock()

        with _patch_now(SEASON_RESUMES_NIGHT):
            applied = await controller.apply_calculation(cover_config_no_sun_open, None)

        assert applied is False
        mock_hass.services.async_call.assert_not_awaited()

    async def test_tracking_resumes_in_daylight(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        store: SeasonRestStore,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Once the sun is back on the facade the group tracks again."""
        mock_hass.states.get.return_value = _cover_state(position=50, tilt=40)
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(datetime(2027, 3, 15, 12, 0)):
            applied = await _controller(mock_hass, store).apply_calculation(
                cover_config_default, calculation_result_direct_sun
            )

        assert applied is True
