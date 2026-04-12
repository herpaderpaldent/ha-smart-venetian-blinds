"""Tests for GroupState throttling logic."""

from __future__ import annotations

from datetime import UTC, datetime

from freezegun import freeze_time
import pytest

from custom_components.smart_venetian_blinds.coordinator.state import GroupState
from custom_components.smart_venetian_blinds.sun.math import SlatCalculationResult, SunPosition


@pytest.mark.unit
class TestGroupStateInit:
    """Tests for GroupState initialization."""

    def test_default_values(self) -> None:
        """GroupState initializes with correct defaults."""
        state = GroupState()
        assert state.sun_position is None
        assert state.calculation is None
        assert state.last_applied_angle is None
        assert state.last_applied_time is None
        assert state.auto_control_enabled is True
        assert state.cover_positions == {}

    def test_custom_auto_control(self) -> None:
        """GroupState can be created with custom auto_control."""
        state = GroupState(auto_control_enabled=False)
        assert state.auto_control_enabled is False


@pytest.mark.unit
class TestShouldApply:
    """Tests for GroupState.should_apply method."""

    def test_first_application_always_allowed(self) -> None:
        """First application is always allowed."""
        state = GroupState()
        result = state.should_apply(
            new_angle=45.0,
            threshold_deg=5.0,
            min_interval_sec=60,
        )
        assert result is True

    def test_none_last_applied_angle_allows_apply(self) -> None:
        """If last_applied_angle is None, allow apply."""
        state = GroupState(last_applied_time=datetime.now())
        result = state.should_apply(
            new_angle=45.0,
            threshold_deg=5.0,
            min_interval_sec=60,
        )
        assert result is True

    def test_none_last_applied_time_allows_apply(self) -> None:
        """If last_applied_time is None, allow apply."""
        state = GroupState(last_applied_angle=45.0)
        result = state.should_apply(
            new_angle=50.0,
            threshold_deg=5.0,
            min_interval_sec=60,
        )
        assert result is True

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_blocks_within_min_interval(self) -> None:
        """Blocks updates within min_interval."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 59, 30, tzinfo=UTC)  # 30 sec ago

        result = state.should_apply(
            new_angle=60.0,  # Big change
            threshold_deg=5.0,
            min_interval_sec=60,  # Requires 60 sec
        )
        assert result is False

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_allows_after_min_interval(self) -> None:
        """Allows updates after min_interval elapsed."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 58, 59, tzinfo=UTC)  # 61 sec ago

        result = state.should_apply(
            new_angle=60.0,  # Big change
            threshold_deg=5.0,
            min_interval_sec=60,
        )
        assert result is True

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_blocks_below_threshold(self) -> None:
        """Blocks updates below threshold even after interval."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 58, 0, tzinfo=UTC)  # 2 min ago

        result = state.should_apply(
            new_angle=47.0,  # Only 2 deg change
            threshold_deg=5.0,  # Requires 5 deg
            min_interval_sec=60,
        )
        assert result is False

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_allows_at_threshold(self) -> None:
        """Allows updates exactly at threshold."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 58, 0, tzinfo=UTC)  # 2 min ago

        result = state.should_apply(
            new_angle=50.0,  # Exactly 5 deg change
            threshold_deg=5.0,
            min_interval_sec=60,
        )
        assert result is True

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_allows_above_threshold(self) -> None:
        """Allows updates above threshold."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 58, 0, tzinfo=UTC)  # 2 min ago

        result = state.should_apply(
            new_angle=55.0,  # 10 deg change
            threshold_deg=5.0,
            min_interval_sec=60,
        )
        assert result is True

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_negative_angle_change(self) -> None:
        """Handles negative angle changes correctly."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 58, 0, tzinfo=UTC)  # 2 min ago

        result = state.should_apply(
            new_angle=35.0,  # -10 deg change (absolute: 10)
            threshold_deg=5.0,
            min_interval_sec=60,
        )
        assert result is True

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_exactly_at_interval_boundary(self) -> None:
        """Tests behavior exactly at min_interval boundary."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 59, 0, tzinfo=UTC)  # Exactly 60 sec ago

        result = state.should_apply(
            new_angle=60.0,  # Big change
            threshold_deg=5.0,
            min_interval_sec=60,
        )
        # 60 sec elapsed is NOT < 60, so it passes interval check
        assert result is True

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_zero_threshold(self) -> None:
        """Zero threshold allows any change."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 58, 0, tzinfo=UTC)  # 2 min ago

        result = state.should_apply(
            new_angle=45.1,  # Tiny change
            threshold_deg=0.0,
            min_interval_sec=60,
        )
        assert result is True

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_zero_interval(self) -> None:
        """Zero interval allows immediate updates."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 59, 59, tzinfo=UTC)  # 1 sec ago

        result = state.should_apply(
            new_angle=60.0,  # Big change
            threshold_deg=5.0,
            min_interval_sec=0,
        )
        assert result is True


@pytest.mark.unit
class TestMarkApplied:
    """Tests for GroupState.mark_applied method."""

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_updates_angle(self) -> None:
        """mark_applied updates last_applied_angle."""
        state = GroupState()
        state.mark_applied(45.0)
        assert state.last_applied_angle == 45.0

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_updates_time(self) -> None:
        """mark_applied updates last_applied_time to now."""
        state = GroupState()
        state.mark_applied(45.0)
        assert state.last_applied_time == datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

    @freeze_time("2024-01-15 12:00:00+00:00")
    def test_overwrites_previous_values(self) -> None:
        """mark_applied overwrites previous values."""
        state = GroupState()
        state.last_applied_angle = 30.0
        state.last_applied_time = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)

        state.mark_applied(60.0)

        assert state.last_applied_angle == 60.0
        assert state.last_applied_time == datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.mark.unit
class TestResetThrottle:
    """Tests for GroupState.reset_throttle method."""

    def test_clears_time_only(self) -> None:
        """reset_throttle clears time but keeps angle."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        state.reset_throttle()

        assert state.last_applied_time is None
        assert state.last_applied_angle == 45.0  # Angle preserved

    def test_enables_immediate_apply(self) -> None:
        """After reset_throttle, should_apply returns True."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime.now()  # Just now

        state.reset_throttle()

        result = state.should_apply(
            new_angle=46.0,  # Small change
            threshold_deg=5.0,
            min_interval_sec=3600,  # Very long interval
        )
        assert result is True


@pytest.mark.unit
class TestResetForFreshStart:
    """Tests for GroupState.reset_for_fresh_start method."""

    def test_clears_sun_tracking(self) -> None:
        """reset_for_fresh_start clears sun_has_hit_facade and no_sun_action_applied."""
        state = GroupState(sun_has_hit_facade=True, no_sun_action_applied=True)

        state.reset_for_fresh_start()

        assert state.sun_has_hit_facade is False
        assert state.no_sun_action_applied is False

    def test_clears_throttle_state(self) -> None:
        """reset_for_fresh_start clears both last_applied_angle and last_applied_time."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        state.reset_for_fresh_start()

        assert state.last_applied_angle is None
        assert state.last_applied_time is None

    def test_enables_immediate_apply(self) -> None:
        """After reset_for_fresh_start, should_apply returns True."""
        state = GroupState()
        state.last_applied_angle = 45.0
        state.last_applied_time = datetime.now()

        state.reset_for_fresh_start()

        result = state.should_apply(
            new_angle=46.0,
            threshold_deg=5.0,
            min_interval_sec=3600,
        )
        assert result is True

    def test_preserves_other_state(self) -> None:
        """reset_for_fresh_start preserves auto_control and cover_positions."""
        state = GroupState(auto_control_enabled=False)
        state.cover_positions["cover.test"] = 75.0

        state.reset_for_fresh_start()

        assert state.auto_control_enabled is False
        assert state.cover_positions["cover.test"] == 75.0


@pytest.mark.unit
class TestGroupStateAttributes:
    """Tests for GroupState attribute storage."""

    def test_sun_position_storage(self, sun_position_midday: SunPosition) -> None:
        """GroupState can store SunPosition."""
        state = GroupState()
        state.sun_position = sun_position_midday
        assert state.sun_position == sun_position_midday

    def test_calculation_storage(self, calculation_result_direct_sun: SlatCalculationResult) -> None:
        """GroupState can store SlatCalculationResult."""
        state = GroupState()
        state.calculation = calculation_result_direct_sun
        assert state.calculation == calculation_result_direct_sun

    def test_cover_positions_dict(self) -> None:
        """GroupState cover_positions is a mutable dict."""
        state = GroupState()
        state.cover_positions["cover.test"] = 75.0
        assert state.cover_positions["cover.test"] == 75.0

    def test_auto_control_toggle(self) -> None:
        """GroupState auto_control can be toggled."""
        state = GroupState()
        assert state.auto_control_enabled is True
        state.auto_control_enabled = False
        assert state.auto_control_enabled is False
