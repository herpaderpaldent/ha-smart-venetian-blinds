"""
Base entity class for smart_venetian_blinds.

This module provides the base class for every entity that belongs to a window
group. It owns the four things each of those entities used to repeat verbatim:
attribution, unique id, entity id and device info.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import ATTRIBUTION
from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.entity_utils import build_entity_id, create_window_group_device_info
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class SmartVenetianBlindsEntity(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator]):
    """
    Base entity class for window group entities.

    Mixed in ahead of the platform entity class, it provides:
    - Automatic coordinator updates
    - The window group device
    - A unique id of ``{entry_id}_{key}``
    - A language-independent entity id (see ``entity_utils.build_entity_id``)
    - Attribution and naming conventions

    Per-cover entities (``ExitModeSwitch``) do not use this class: they are named
    after their cover rather than the group, and their unique id carries the
    subentry id.
    """

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
        entity_description: EntityDescription,
        *,
        platform: str,
    ) -> None:
        """
        Initialize the base entity.

        Args:
            coordinator: The data update coordinator for this entity.
            entity_description: The entity description defining characteristics.
            platform: The platform the entity belongs to, e.g. ``sensor``. Needed
                for the entity id; Home Assistant only knows it once the entity
                is added.
        """
        super().__init__(coordinator)
        self.entity_description = entity_description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{entity_description.key}"
        self.entity_id = build_entity_id(platform, entry.title, entity_description.key)
        self._attr_device_info = create_window_group_device_info(entry)
