"""Tests for SeasonalPausePipe."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.smart_venetian_blinds.cover_control.context import CoverContext, CoverTrackingState
from custom_components.smart_venetian_blinds.cover_control.pipes.seasonal_pause import SeasonalPausePipe
from custom_components.smart_venetian_blinds.season import SeasonWindow
from tests.conftest import create_mock_state

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.cover_control.controller import CoverConfig
    from custom_components.smart_venetian_blinds.sun.math import SlatCalculationResult

SEASON = SeasonWindow(enabled=True, start_month=3, start_day=15, end_month=10, end_day=15, rest_position=100)

IN_SEASON = datetime(2026, 7, 1, 12, 0)
PAUSED = datetime(2026, 11, 1, 12, 0)


def _patch_now(moment: datetime) -> object:
    """Patch the pipe's clock to a fixed moment."""
    return patch(
        "custom_components.smart_venetian_blinds.cover_control.pipes.seasonal_pause.dt_util.now",
        return_value=moment,
    )


def _context(
    config: CoverConfig,
    hass: MagicMock,
    state: CoverTrackingState,
    calculation: SlatCalculationResult | None,
) -> CoverContext:
    """Build a pipeline context for the pipe under test."""
    return CoverContext(config=config, calculation=calculation, hass=hass, state=state)


@pytest.mark.unit
class TestSeasonalPausePipeInSeason:
    """Pipe behavior while the group is inside its season."""

    async def test_passes_through(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Inside the season the pipe hands control to the next pipe."""
        pipe = SeasonalPausePipe(SEASON, position_timeout_sec=5)
        ctx = _context(cover_config_default, mock_hass, CoverTrackingState(), calculation_result_direct_sun)
        call_next = AsyncMock(return_value=True)

        with _patch_now(IN_SEASON):
            result = await pipe.handle(ctx, call_next)

        assert result is True
        call_next.assert_awaited_once()

    async def test_disabled_season_passes_through(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """A disabled seasonal pause never blocks, even out of season."""
        pipe = SeasonalPausePipe(SeasonWindow(enabled=False), position_timeout_sec=5)
        ctx = _context(cover_config_default, mock_hass, CoverTrackingState(), calculation_result_direct_sun)
        call_next = AsyncMock(return_value=True)

        with _patch_now(PAUSED):
            result = await pipe.handle(ctx, call_next)

        assert result is True
        call_next.assert_awaited_once()

    async def test_season_start_resets_tracking_state(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """When the season starts again, stale pause state is cleared."""
        pipe = SeasonalPausePipe(SEASON, position_timeout_sec=5)
        state = CoverTrackingState(season_rest_applied=True, exit_paused=True, in_no_sun=True)
        ctx = _context(cover_config_default, mock_hass, state, calculation_result_direct_sun)
        call_next = AsyncMock(return_value=False)

        with _patch_now(IN_SEASON):
            await pipe.handle(ctx, call_next)

        assert state.season_rest_applied is False
        assert state.exit_paused is False
        assert state.in_no_sun is False
        call_next.assert_awaited_once()


@pytest.mark.unit
class TestSeasonalPausePipeOutOfSeason:
    """Pipe behavior while the group is seasonally paused."""

    async def test_defers_rest_drive_until_sun_is_up(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
    ) -> None:
        """With the sun below the horizon no cover is moved."""
        pipe = SeasonalPausePipe(SEASON, position_timeout_sec=5)
        state = CoverTrackingState()
        ctx = _context(cover_config_default, mock_hass, state, None)
        call_next = AsyncMock()
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(PAUSED):
            result = await pipe.handle(ctx, call_next)

        assert result is False
        assert state.season_rest_applied is False
        call_next.assert_not_awaited()
        mock_hass.services.async_call.assert_not_awaited()

    async def test_drives_to_rest_position_once(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """The first sunlit cycle of the pause drives the cover to the rest position."""
        pipe = SeasonalPausePipe(SEASON, position_timeout_sec=5)
        state = CoverTrackingState()
        ctx = _context(cover_config_default, mock_hass, state, calculation_result_direct_sun)
        call_next = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(attributes={"current_position": 20})
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(PAUSED), patch.object(pipe, "_wait_for_position", AsyncMock(return_value=True)):
            result = await pipe.handle(ctx, call_next)

        assert result is True
        assert state.season_rest_applied is True
        call_next.assert_not_awaited()
        mock_hass.services.async_call.assert_awaited_once()
        args = mock_hass.services.async_call.await_args
        assert args[0][1] == "set_cover_position"
        assert args[0][2]["position"] == 100

    async def test_second_cycle_does_not_move_cover(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Once the rest position is applied, further cycles are a no-op."""
        pipe = SeasonalPausePipe(SEASON, position_timeout_sec=5)
        state = CoverTrackingState(season_rest_applied=True)
        ctx = _context(cover_config_default, mock_hass, state, calculation_result_direct_sun)
        call_next = AsyncMock()
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(PAUSED):
            result = await pipe.handle(ctx, call_next)

        assert result is False
        call_next.assert_not_awaited()
        mock_hass.services.async_call.assert_not_awaited()

    async def test_already_at_rest_position_skips_command(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """A cover already at the rest position is marked done without a service call."""
        pipe = SeasonalPausePipe(SEASON, position_timeout_sec=5)
        state = CoverTrackingState()
        ctx = _context(cover_config_default, mock_hass, state, calculation_result_direct_sun)
        mock_hass.states.get.return_value = create_mock_state(attributes={"current_position": 99})
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(PAUSED):
            result = await pipe.handle(ctx, AsyncMock())

        assert result is False
        assert state.season_rest_applied is True
        mock_hass.services.async_call.assert_not_awaited()

    async def test_unavailable_cover_retries_next_cycle(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """An unavailable cover leaves the flag unset so the drive is retried."""
        pipe = SeasonalPausePipe(SEASON, position_timeout_sec=5)
        state = CoverTrackingState()
        ctx = _context(cover_config_default, mock_hass, state, calculation_result_direct_sun)
        mock_hass.states.get.return_value = None
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(PAUSED):
            result = await pipe.handle(ctx, AsyncMock())

        assert result is False
        assert state.season_rest_applied is False
        mock_hass.services.async_call.assert_not_awaited()

    async def test_unknown_position_still_drives(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """A cover that does not report a position is commanded anyway."""
        pipe = SeasonalPausePipe(SEASON, position_timeout_sec=5)
        state = CoverTrackingState()
        ctx = _context(cover_config_default, mock_hass, state, calculation_result_direct_sun)
        mock_hass.states.get.return_value = create_mock_state(attributes={})
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(PAUSED), patch.object(pipe, "_wait_for_position", AsyncMock(return_value=True)):
            result = await pipe.handle(ctx, AsyncMock())

        assert result is True
        assert state.season_rest_applied is True
        mock_hass.services.async_call.assert_awaited_once()

    async def test_custom_rest_position(
        self,
        cover_config_default: CoverConfig,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """The configured rest position is used for the one-time drive."""
        season = SeasonWindow(enabled=True, start_month=3, start_day=15, end_month=10, end_day=15, rest_position=40)
        pipe = SeasonalPausePipe(season, position_timeout_sec=5)
        ctx = _context(cover_config_default, mock_hass, CoverTrackingState(), calculation_result_direct_sun)
        mock_hass.states.get.return_value = create_mock_state(attributes={"current_position": 0})
        mock_hass.services.async_call = AsyncMock()

        with _patch_now(PAUSED), patch.object(pipe, "_wait_for_position", AsyncMock(return_value=True)):
            await pipe.handle(ctx, AsyncMock())

        assert mock_hass.services.async_call.await_args[0][2]["position"] == 40
