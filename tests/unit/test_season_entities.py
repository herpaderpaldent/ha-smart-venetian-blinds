"""Tests for the season entities on the window group device."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.smart_venetian_blinds.binary_sensor.seasonal_pause import SeasonalPauseBinarySensor
from custom_components.smart_venetian_blinds.const import (
    CONF_SEASON_END_DAY,
    CONF_SEASON_END_MONTH,
    CONF_SEASON_PAUSE_ENABLED,
    CONF_SEASON_START_DAY,
    CONF_SEASON_START_MONTH,
)
from custom_components.smart_venetian_blinds.select.season_days import SeasonEndSelect, SeasonStartSelect
from custom_components.smart_venetian_blinds.switch.season_pause import SeasonPauseSwitch

OPTIONS = {
    CONF_SEASON_PAUSE_ENABLED: True,
    CONF_SEASON_START_MONTH: 3,
    CONF_SEASON_START_DAY: 15,
    CONF_SEASON_END_MONTH: 10,
    CONF_SEASON_END_DAY: 15,
}


def _coordinator(options: dict | None = None) -> MagicMock:
    """Build a mock coordinator whose entry carries the given options."""
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "entry-1"
    coordinator.config_entry.title = "South Windows"
    coordinator.config_entry.options = dict(OPTIONS if options is None else options)
    return coordinator


def _attach_hass(entity: object, language: str = "en") -> MagicMock:
    """Give an entity a mock hass with a configured language."""
    hass = MagicMock()
    hass.config.language = language
    entity.hass = hass  # type: ignore[attr-defined]
    return hass


def _written_options(hass: MagicMock) -> dict:
    """Return the options passed to the last async_update_entry call."""
    return hass.config_entries.async_update_entry.call_args.kwargs["options"]


@pytest.mark.unit
class TestSeasonBoundarySelects:
    """Tests for the two boundary select entities."""

    def test_current_option_is_the_localized_label(self) -> None:
        """The stored month/day renders in Home Assistant's language."""
        start, end = SeasonStartSelect(_coordinator()), SeasonEndSelect(_coordinator())
        _attach_hass(start, "de")
        _attach_hass(end, "de")

        assert start.current_option == "15. März"
        assert end.current_option == "15. Oktober"

    def test_current_option_is_always_selectable(self) -> None:
        """The reported option must be one of the offered ones, in any language."""
        for language in ("en", "de", "fr"):
            entity = SeasonStartSelect(_coordinator())
            _attach_hass(entity, language)
            assert entity.current_option in entity.options

    def test_no_year_is_exposed(self) -> None:
        """Nothing in the entity surface mentions a year, so nothing drifts at New Year."""
        entity = SeasonStartSelect(_coordinator())
        _attach_hass(entity)

        assert "202" not in entity.current_option
        assert not any("202" in option for option in entity.options)

    def test_unique_id_follows_the_convention(self) -> None:
        """Entities keep the integration's {entry_id}_{key} scheme."""
        assert SeasonStartSelect(_coordinator()).unique_id == "entry-1_season_start"

    async def test_selecting_stores_month_and_day(self) -> None:
        """Choosing a label writes the matching month and day."""
        entity = SeasonStartSelect(_coordinator())
        hass = _attach_hass(entity, "de")

        await entity.async_select_option("1. April")

        options = _written_options(hass)
        assert (options[CONF_SEASON_START_MONTH], options[CONF_SEASON_START_DAY]) == (4, 1)

    async def test_selecting_preserves_other_options(self) -> None:
        """Writing one boundary keeps every other option intact."""
        entity = SeasonEndSelect(_coordinator({**OPTIONS, "change_threshold_deg": 7}))
        hass = _attach_hass(entity)

        await entity.async_select_option("30 September")

        options = _written_options(hass)
        assert (options[CONF_SEASON_END_MONTH], options[CONF_SEASON_END_DAY]) == (9, 30)
        assert options[CONF_SEASON_START_MONTH] == 3
        assert options["change_threshold_deg"] == 7

    async def test_leap_day_round_trips(self) -> None:
        """29 February can be chosen and comes back unchanged."""
        entity = SeasonEndSelect(_coordinator())
        hass = _attach_hass(entity)

        await entity.async_select_option("29 February")

        options = _written_options(hass)
        assert (options[CONF_SEASON_END_MONTH], options[CONF_SEASON_END_DAY]) == (2, 29)

        stored = SeasonEndSelect(_coordinator({**OPTIONS, **options}))
        _attach_hass(stored)
        assert stored.current_option == "29 February"


@pytest.mark.unit
class TestSeasonPauseSwitch:
    """Tests for the switch that enables the seasonal schedule."""

    def test_is_on_reflects_options(self) -> None:
        """The switch mirrors the stored enabled flag."""
        assert SeasonPauseSwitch(_coordinator()).is_on is True
        assert SeasonPauseSwitch(_coordinator({**OPTIONS, CONF_SEASON_PAUSE_ENABLED: False})).is_on is False

    async def test_turn_on_and_off(self) -> None:
        """Toggling writes the flag without touching the window."""
        switch = SeasonPauseSwitch(_coordinator({**OPTIONS, CONF_SEASON_PAUSE_ENABLED: False}))
        hass = _attach_hass(switch)

        await switch.async_turn_on()
        assert _written_options(hass)[CONF_SEASON_PAUSE_ENABLED] is True
        assert _written_options(hass)[CONF_SEASON_START_MONTH] == 3

        await switch.async_turn_off()
        assert _written_options(hass)[CONF_SEASON_PAUSE_ENABLED] is False


@pytest.mark.unit
class TestSeasonalPauseBinarySensor:
    """Tests for the sensor reporting whether the group is paused right now."""

    def _sensor(self, options: dict | None = None) -> SeasonalPauseBinarySensor:
        """Build the sensor with a mock coordinator."""
        return SeasonalPauseBinarySensor(_coordinator(options))

    @pytest.mark.parametrize(
        ("today", "expected"),
        [
            (datetime(2026, 7, 1), False),
            (datetime(2026, 10, 15), False),
            (datetime(2026, 10, 16), True),
            (datetime(2027, 3, 14), True),
            (datetime(2027, 3, 15), False),
        ],
    )
    def test_flips_on_the_boundary(self, today: datetime, expected: bool) -> None:
        """The sensor is on exactly while covers are not being driven."""
        with patch(
            "custom_components.smart_venetian_blinds.binary_sensor.seasonal_pause.dt_util.now",
            return_value=today,
        ):
            assert self._sensor().is_on is expected

    def test_off_when_the_schedule_is_disabled(self) -> None:
        """Without a seasonal schedule the group is never paused."""
        with patch(
            "custom_components.smart_venetian_blinds.binary_sensor.seasonal_pause.dt_util.now",
            return_value=datetime(2026, 12, 1),
        ):
            assert self._sensor({**OPTIONS, CONF_SEASON_PAUSE_ENABLED: False}).is_on is False

    def test_wrapping_window(self) -> None:
        """A season across New Year is reported correctly on both sides."""
        options = {
            **OPTIONS,
            CONF_SEASON_START_MONTH: 11,
            CONF_SEASON_START_DAY: 1,
            CONF_SEASON_END_MONTH: 2,
            CONF_SEASON_END_DAY: 28,
        }
        for moment, expected in ((datetime(2026, 12, 24), False), (datetime(2026, 6, 1), True)):
            with patch(
                "custom_components.smart_venetian_blinds.binary_sensor.seasonal_pause.dt_util.now",
                return_value=moment,
            ):
                assert self._sensor(options).is_on is expected

    def test_attributes_describe_the_window(self) -> None:
        """Dashboards and automations can read the configured window."""
        attributes = self._sensor().extra_state_attributes

        assert attributes["season_start"] == "03-15"
        assert attributes["season_end"] == "10-15"
        assert attributes["season_pause_enabled"] is True
        assert attributes["rest_position"] == 100


@pytest.mark.unit
class TestEntityIds:
    """Tests for entity ids staying valid and language-independent."""

    def test_umlaut_group_name_yields_a_valid_entity_id(self) -> None:
        """A group called "Büro" must not produce an entity id Home Assistant rejects."""
        from homeassistant.core import valid_entity_id  # noqa: PLC0415

        coordinator = _coordinator()
        coordinator.config_entry.title = "Büro"

        for entity in (
            SeasonStartSelect(coordinator),
            SeasonEndSelect(coordinator),
            SeasonPauseSwitch(coordinator),
            SeasonalPauseBinarySensor(coordinator),
        ):
            assert valid_entity_id(entity.entity_id), entity.entity_id

    def test_entity_id_does_not_follow_the_ui_language(self) -> None:
        """Automations must not break when the user switches Home Assistant's language."""
        entity = SeasonStartSelect(_coordinator())
        _attach_hass(entity, "de")

        assert entity.entity_id == "select.south_windows_season_start"
