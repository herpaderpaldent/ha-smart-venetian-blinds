"""Tests for the shared cover position helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from custom_components.smart_venetian_blinds.cover_control.position import (
    POSITION_TOLERANCE_PERCENT,
    async_wait_for_position,
    is_at_position,
    read_position,
)
from tests.conftest import create_mock_state

if TYPE_CHECKING:
    from unittest.mock import MagicMock

ENTITY_ID = "cover.test_blinds"


@pytest.mark.unit
class TestReadPosition:
    """read_position must never raise, whatever the cover reports."""

    def test_reads_current_position(self, mock_hass: MagicMock) -> None:
        """A numeric position is returned as an int."""
        mock_hass.states.get.return_value = create_mock_state(attributes={"current_position": 42})

        assert read_position(mock_hass, ENTITY_ID) == 42

    def test_casts_string_position(self, mock_hass: MagicMock) -> None:
        """Covers reporting a string position are still readable."""
        mock_hass.states.get.return_value = create_mock_state(attributes={"current_position": "42"})

        assert read_position(mock_hass, ENTITY_ID) == 42

    def test_unavailable_cover(self, mock_hass: MagicMock) -> None:
        """A missing state reads as unknown."""
        mock_hass.states.get.return_value = None

        assert read_position(mock_hass, ENTITY_ID) is None

    def test_missing_attribute(self, mock_hass: MagicMock) -> None:
        """A cover without a position attribute reads as unknown."""
        mock_hass.states.get.return_value = create_mock_state(attributes={})

        assert read_position(mock_hass, ENTITY_ID) is None

    def test_unreadable_value(self, mock_hass: MagicMock) -> None:
        """A non-numeric position reads as unknown instead of raising."""
        mock_hass.states.get.return_value = create_mock_state(attributes={"current_position": "unknown"})

        assert read_position(mock_hass, ENTITY_ID) is None


@pytest.mark.unit
class TestIsAtPosition:
    """The tolerance band around a target position."""

    def test_exact_match(self) -> None:
        """The target itself counts as arrived."""
        assert is_at_position(50, 50) is True

    def test_within_tolerance(self) -> None:
        """A deviation up to the tolerance counts as arrived."""
        assert is_at_position(50 + POSITION_TOLERANCE_PERCENT, 50) is True

    def test_outside_tolerance(self) -> None:
        """A larger deviation does not."""
        assert is_at_position(50 + POSITION_TOLERANCE_PERCENT + 1, 50) is False

    def test_unknown_position(self) -> None:
        """An unknown position never counts as arrived."""
        assert is_at_position(None, 50) is False


@pytest.mark.unit
class TestAsyncWaitForPosition:
    """Waiting for a cover to arrive."""

    async def test_returns_immediately_when_already_there(self, mock_hass: MagicMock) -> None:
        """A cover at the target is not polled a second time."""
        mock_hass.states.get.return_value = create_mock_state(attributes={"current_position": 100})

        assert await async_wait_for_position(mock_hass, ENTITY_ID, 100, 10) is True

    async def test_times_out(self, mock_hass: MagicMock) -> None:
        """A cover that never arrives times out rather than waiting forever."""
        mock_hass.states.get.return_value = create_mock_state(attributes={"current_position": 0})

        assert await async_wait_for_position(mock_hass, ENTITY_ID, 100, 0) is False
