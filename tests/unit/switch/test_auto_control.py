"""Tests for AutoControlSwitch."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.smart_venetian_blinds.coordinator.state import GroupState
from custom_components.smart_venetian_blinds.data import SmartVenetianBlindsData
from custom_components.smart_venetian_blinds.switch.auto_control import AutoControlSwitch


def _make_switch(state: GroupState, apply_fn: AsyncMock | None = None) -> AutoControlSwitch:
    """Create an AutoControlSwitch with mocked dependencies."""
    runtime_data = MagicMock(spec=SmartVenetianBlindsData)
    runtime_data.state = state
    runtime_data.apply_cover_tilts = apply_fn
    # Wire auto_control_enabled through to state
    type(runtime_data).auto_control_enabled = property(
        lambda self: self.state.auto_control_enabled,
        lambda self, v: setattr(self.state, "auto_control_enabled", v),
    )

    coordinator = MagicMock()
    coordinator.config_entry.runtime_data = runtime_data
    coordinator.config_entry.entry_id = "test_entry_123"
    coordinator.config_entry.title = "test_group"
    coordinator.trigger_update = MagicMock()

    switch = AutoControlSwitch(coordinator)
    # Patch async_write_ha_state since there is no real HA runtime
    switch.async_write_ha_state = MagicMock()
    return switch


@pytest.mark.unit
class TestAutoControlTurnOn:
    """Tests for async_turn_on behavior."""

    @pytest.mark.asyncio
    async def test_turn_on_enables_auto_control(self) -> None:
        """Turning on sets auto_control_enabled to True."""
        state = GroupState(auto_control_enabled=False)
        switch = _make_switch(state)

        await switch.async_turn_on()

        assert state.auto_control_enabled is True

    @pytest.mark.asyncio
    async def test_turn_on_resets_state_for_fresh_start(self) -> None:
        """Turning on resets sun_has_hit_facade, no_sun_action_applied, and throttle."""
        state = GroupState(
            auto_control_enabled=False,
            sun_has_hit_facade=True,
            no_sun_action_applied=True,
            last_applied_angle=45.0,
            last_applied_time=datetime(2024, 1, 15, 12, 0, 0),
        )
        switch = _make_switch(state)

        await switch.async_turn_on()

        assert state.sun_has_hit_facade is False
        assert state.no_sun_action_applied is False
        assert state.last_applied_angle is None
        assert state.last_applied_time is None

    @pytest.mark.asyncio
    async def test_turn_on_triggers_coordinator_update(self) -> None:
        """Turning on triggers a coordinator update for sensor recalculation."""
        state = GroupState(auto_control_enabled=False)
        switch = _make_switch(state)

        await switch.async_turn_on()

        switch.coordinator.trigger_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_on_calls_apply_cover_tilts(self) -> None:
        """Turning on calls the stored apply_cover_tilts callable."""
        state = GroupState(auto_control_enabled=False)
        apply_fn = AsyncMock()
        switch = _make_switch(state, apply_fn=apply_fn)

        await switch.async_turn_on()

        apply_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_turn_on_without_apply_fn(self) -> None:
        """Turning on works when apply_cover_tilts is None."""
        state = GroupState(auto_control_enabled=False)
        switch = _make_switch(state, apply_fn=None)

        await switch.async_turn_on()

        assert state.auto_control_enabled is True

    @pytest.mark.asyncio
    async def test_turn_on_writes_ha_state(self) -> None:
        """Turning on writes HA state."""
        state = GroupState(auto_control_enabled=False)
        switch = _make_switch(state)

        await switch.async_turn_on()

        switch.async_write_ha_state.assert_called_once()


@pytest.mark.unit
class TestAutoControlTurnOff:
    """Tests for async_turn_off behavior."""

    @pytest.mark.asyncio
    async def test_turn_off_disables_auto_control(self) -> None:
        """Turning off sets auto_control_enabled to False."""
        state = GroupState(auto_control_enabled=True)
        switch = _make_switch(state)

        await switch.async_turn_off()

        assert state.auto_control_enabled is False

    @pytest.mark.asyncio
    async def test_turn_off_writes_ha_state(self) -> None:
        """Turning off writes HA state."""
        state = GroupState(auto_control_enabled=True)
        switch = _make_switch(state)

        await switch.async_turn_off()

        switch.async_write_ha_state.assert_called_once()
