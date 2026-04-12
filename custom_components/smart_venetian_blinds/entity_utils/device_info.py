"""Device info utilities for smart_venetian_blinds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import DOMAIN
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


def create_window_group_device_info(config_entry: ConfigEntry) -> DeviceInfo:
    """
    Create a DeviceInfo object for a window group entity.

    Args:
        config_entry: The config entry representing the window group.

    Returns:
        A DeviceInfo object identifying the window group device.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name=config_entry.title,
        manufacturer="Smart Venetian Blinds",
        model="Window Group",
        entry_type=DeviceEntryType.SERVICE,
    )
