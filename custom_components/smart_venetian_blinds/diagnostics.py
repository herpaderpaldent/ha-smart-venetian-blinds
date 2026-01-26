"""
Diagnostics support for smart_venetian_blinds.

Provides diagnostic information about the integration state for troubleshooting.

Learn more about diagnostics:
https://developers.home-assistant.io/docs/core/integration_diagnostics
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers import device_registry as dr, entity_registry as er

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import SmartVenetianBlindsConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: SmartVenetianBlindsConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    sun_provider = entry.runtime_data.sun_provider
    state = entry.runtime_data.state
    integration = entry.runtime_data.integration

    # Get device and entity information
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    # Find all devices for this integration
    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    device_info = []
    for device in devices:
        entities = er.async_entries_for_device(entity_reg, device.id)
        device_info.append(
            {
                "id": device.id,
                "name": device.name,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "entity_count": len(entities),
                "entities": [
                    {
                        "entity_id": entity.entity_id,
                        "platform": entity.platform,
                        "original_name": entity.original_name,
                        "disabled": entity.disabled,
                    }
                    for entity in entities
                ],
            }
        )

    # Sun data information
    sun_position = sun_provider.get_sun_position()
    sun_info = {
        "available": sun_provider.is_available,
        "tracked_entities": sun_provider.get_tracked_entities(),
        "current_position": {
            "azimuth_deg": sun_position.azimuth_deg if sun_position else None,
            "elevation_deg": sun_position.elevation_deg if sun_position else None,
        }
        if sun_position
        else None,
    }

    # Coordinator information
    coordinator_info = {
        "last_update_success": coordinator.last_update_success,
        "change_threshold": coordinator.change_threshold,
        "min_update_interval": coordinator.min_update_interval,
    }

    # Calculation result
    calculation_info = None
    if coordinator.data:
        calculation_info = {
            "slat_angle_deg": coordinator.data.slat_angle_deg,
            "slat_tilt_percent": coordinator.data.slat_tilt_percent,
            "profile_angle_deg": coordinator.data.profile_angle_deg,
            "sun_is_behind_facade": coordinator.data.sun_is_behind_facade,
        }

    # Group state
    state_info = {
        "auto_control_enabled": state.auto_control_enabled,
        "last_applied_angle": state.last_applied_angle,
        "last_applied_time": state.last_applied_time.isoformat() if state.last_applied_time else None,
    }

    # Group configuration
    group_info = coordinator.get_group_data()

    # Subentry (cover) information
    covers_info = []
    for subentry_id, subentry in entry.subentries.items():
        covers_info.append(
            {
                "subentry_id": subentry_id,
                "title": subentry.title,
                "data": dict(subentry.data),
            }
        )

    # Integration information
    integration_info = {
        "name": integration.name,
        "version": integration.version,
        "domain": integration.domain,
    }

    # Config entry details
    entry_info = {
        "entry_id": entry.entry_id,
        "version": entry.version,
        "title": entry.title,
        "state": str(entry.state),
        "unique_id": entry.unique_id,
        "data": dict(entry.data),
        "options": dict(entry.options),
    }

    return {
        "entry": entry_info,
        "integration": integration_info,
        "group": group_info,
        "sun": sun_info,
        "coordinator": coordinator_info,
        "calculation": calculation_info,
        "state": state_info,
        "covers": covers_info,
        "devices": device_info,
    }
