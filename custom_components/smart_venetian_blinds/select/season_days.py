"""
Season boundary select entities for smart_venetian_blinds.

Exposes the seasonal pause window on the window group's device page, alongside
the slat geometry numbers, so the season can be adjusted without opening the
options flow.

A select rather than a date: only month and day are stored, and Home Assistant
has no month/day entity. A date entity would show a year that means nothing and
would change state on its own every New Year.
"""

from __future__ import annotations

from custom_components.smart_venetian_blinds.const import (
    ATTRIBUTION,
    CONF_SEASON_END_DAY,
    CONF_SEASON_END_MONTH,
    CONF_SEASON_START_DAY,
    CONF_SEASON_START_MONTH,
)
from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.entity_utils import (
    async_merge_entry_options,
    build_entity_id,
    create_window_group_device_info,
)
from custom_components.smart_venetian_blinds.season import SeasonWindow, day_choices, format_day, parse_day_value
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

SEASON_START_DESCRIPTION = SelectEntityDescription(
    key="season_start",
    translation_key="season_start",
    entity_category=EntityCategory.CONFIG,
    icon="mdi:calendar-start",
)

SEASON_END_DESCRIPTION = SelectEntityDescription(
    key="season_end",
    translation_key="season_end",
    entity_category=EntityCategory.CONFIG,
    icon="mdi:calendar-end",
)


class SeasonBoundarySelect(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator], SelectEntity):
    """
    Base class for the two season boundary selects.

    Options are the 366 possible boundaries, labelled in Home Assistant's
    configured language. Only month and day are stored, so the season repeats
    every year without reconfiguration.
    """

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    _month_key: str
    _day_key: str

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
        description: SelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self.entity_id = build_entity_id("select", coordinator.config_entry.title, description.key)
        self._attr_device_info = create_window_group_device_info(coordinator.config_entry)

    @property
    def _language(self) -> str | None:
        """Return Home Assistant's configured language, if available."""
        return self.hass.config.language if self.hass else None

    @property
    def options(self) -> list[str]:
        """Return every possible boundary, labelled in Home Assistant's language.

        Built on access rather than in __init__: ``hass`` is not attached yet at
        construction time, so the labels would be stuck on the default language
        while ``current_option`` returned a translated one.
        """
        return [label for _, label in day_choices(self._language)]

    @property
    def _season(self) -> SeasonWindow:
        """Return the season window from the current entry options."""
        return SeasonWindow.from_options(self.coordinator.config_entry.options)

    def _boundary(self) -> tuple[int, int]:
        """Return the stored (month, day) for this boundary."""
        raise NotImplementedError

    @property
    def current_option(self) -> str:
        """Return the stored boundary as its localized label."""
        month, day = self._boundary()
        return format_day(month, day, self._language)

    async def async_select_option(self, option: str) -> None:
        """Store the chosen boundary, keeping only month and day."""
        labels = {label: value for value, label in day_choices(self._language)}
        month, day = parse_day_value(labels[option])
        async_merge_entry_options(
            self.hass,
            self.coordinator.config_entry,
            **{self._month_key: month, self._day_key: day},
        )


class SeasonStartSelect(SeasonBoundarySelect):
    """Select entity for the day the season starts."""

    _month_key = CONF_SEASON_START_MONTH
    _day_key = CONF_SEASON_START_DAY

    def __init__(self, coordinator: SmartVenetianBlindsDataUpdateCoordinator) -> None:
        """Initialize the season start select."""
        super().__init__(coordinator, SEASON_START_DESCRIPTION)

    def _boundary(self) -> tuple[int, int]:
        """Return the stored season start."""
        season = self._season
        return season.start_month, season.start_day


class SeasonEndSelect(SeasonBoundarySelect):
    """Select entity for the last day of the season."""

    _month_key = CONF_SEASON_END_MONTH
    _day_key = CONF_SEASON_END_DAY

    def __init__(self, coordinator: SmartVenetianBlindsDataUpdateCoordinator) -> None:
        """Initialize the season end select."""
        super().__init__(coordinator, SEASON_END_DESCRIPTION)

    def _boundary(self) -> tuple[int, int]:
        """Return the stored season end."""
        season = self._season
        return season.end_month, season.end_day


__all__ = [
    "SEASON_END_DESCRIPTION",
    "SEASON_START_DESCRIPTION",
    "SeasonEndSelect",
    "SeasonStartSelect",
]
