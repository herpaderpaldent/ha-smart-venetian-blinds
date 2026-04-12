"""Device info utilities for smart_venetian_blinds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


def create_device_info(
    config_entry: ConfigEntry,
    name: str | None = None,
    manufacturer: str | None = None,
    model: str | None = None,
    sw_version: str | None = None,
) -> DeviceInfo:
    """
    Create a DeviceInfo object for an entity.

    Args:
        config_entry: The config entry for the integration
        name: Optional device name
        manufacturer: Optional manufacturer name
        model: Optional model name
        sw_version: Optional software version

    Returns:
        A DeviceInfo object with the specified information

    Example:
        >>> device_info = create_device_info(
        ...     config_entry,
        ...     name="My Device",
        ...     manufacturer="Example Corp",
        ...     model="Model X",
        ... )
    """
    return DeviceInfo(
        identifiers={(config_entry.domain, config_entry.entry_id)},
        name=name or "Smart Venetian Blinds",
        manufacturer=manufacturer or "Smart Venetian Blinds",
        model=model or "Unknown",
        sw_version=sw_version,
    )
