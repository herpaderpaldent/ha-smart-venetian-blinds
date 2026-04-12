"""
Apply now service for smart_venetian_blinds.

Forces immediate recalculation and application of slat angles,
bypassing throttling rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall


async def async_handle_apply_now(hass: HomeAssistant, call: ServiceCall) -> None:
    """
    Handle the apply_now service call.

    Forces immediate recalculation and application of slat angles
    to all covers in all window groups, ignoring throttling.

    Args:
        hass: The Home Assistant instance.
        call: The service call data.
    """
    from custom_components.smart_venetian_blinds import _create_controller  # noqa: PLC0415

    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        LOGGER.warning("No config entries found for %s", DOMAIN)
        return

    for entry in entries:
        if not entry.runtime_data:
            continue

        # Check if auto control is enabled for this group
        if not entry.runtime_data.auto_control_enabled:
            LOGGER.info(
                "Auto control disabled for group '%s', skipping apply_now",
                entry.title,
            )
            continue

        # Reset throttle to allow immediate application
        state = entry.runtime_data.state
        state.reset_throttle()

        # Trigger coordinator update
        coordinator = entry.runtime_data.coordinator
        await coordinator.async_refresh()

        # Get the new calculation result
        calculation = coordinator.data

        controller = _create_controller(hass, entry)
        results = await controller.apply_to_all_covers(
            entry.subentries,
            calculation,
        )

        applied_count = sum(1 for applied in results.values() if applied)
        LOGGER.info(
            "Applied tilt to %d/%d covers in group %s",
            applied_count,
            len(results),
            entry.title,
        )


__all__ = ["async_handle_apply_now"]
