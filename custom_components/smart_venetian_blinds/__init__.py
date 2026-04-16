"""
Custom integration to integrate smart_venetian_blinds with Home Assistant.

This integration provides sun-position-driven control for venetian blinds:
- Calculates optimal slat angles based on sun position and facade orientation
- Supports multiple window groups with different orientations
- Allows adding multiple covers per group via subentries
- Respects manual close detection to avoid disturbing sleeping users

For more details about this integration, please refer to:
https://github.com/herpaderpaldent/ha-smart-venetian-blinds
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.loader import async_get_loaded_integration

from .const import (
    CONF_COVER_ENTITY,
    CONF_POSITION_SETTLING_DELAY,
    CONF_POSITION_TIMEOUT,
    DEFAULT_POSITION_SETTLING_DELAY,
    DEFAULT_POSITION_TIMEOUT,
    DOMAIN,
    LOGGER,
)
from .coordinator import SmartVenetianBlindsDataUpdateCoordinator
from .coordinator.state import GroupState
from .cover_control import CoverController
from .cover_control.context import CoverTrackingState
from .data import SmartVenetianBlindsData
from .service_actions import async_setup_services
from .sun import SunDataProvider, SunStateListener

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import SmartVenetianBlindsConfigEntry

PLATFORMS: list[Platform] = [
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _create_controller(hass: HomeAssistant, entry: SmartVenetianBlindsConfigEntry) -> CoverController:
    """Create a CoverController from a config entry's current runtime state."""
    state = entry.runtime_data.state
    return CoverController(
        hass,
        position_timeout_sec=entry.options.get(CONF_POSITION_TIMEOUT, DEFAULT_POSITION_TIMEOUT),
        settling_delay_sec=entry.options.get(CONF_POSITION_SETTLING_DELAY, DEFAULT_POSITION_SETTLING_DELAY),
        cover_states=state.cover_states,
    )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    Set up the integration.

    This is called once at Home Assistant startup to register service actions.
    """
    await async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartVenetianBlindsConfigEntry,
) -> bool:
    """
    Set up this integration using UI.

    This is called when a config entry is loaded. It:
    1. Creates the sun data provider
    2. Initializes the coordinator for slat calculations
    3. Sets up sun state listeners for event-driven updates
    4. Sets up all platforms (sensors, switches)
    """
    # Initialize sun data provider
    sun_provider = SunDataProvider(hass)

    # Initialize coordinator
    coordinator = SmartVenetianBlindsDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        sun_provider=sun_provider,
    )

    # Store runtime data
    entry.runtime_data = SmartVenetianBlindsData(
        sun_provider=sun_provider,
        coordinator=coordinator,
        integration=async_get_loaded_integration(hass, entry.domain),
        state=GroupState(),
    )

    # Perform initial calculation
    await coordinator.async_config_entry_first_refresh()

    # Bug 1 fix: if the sun is currently below the horizon (or unknown), pre-initialize
    # all cover states with in_no_sun=True so the first sunrise triggers the
    # in_no_sun→False transition correctly and bypasses exit detection.
    sun_position = sun_provider.get_sun_position()
    if sun_position is None or sun_position.elevation_deg <= 0:
        state = entry.runtime_data.state
        for subentry in entry.subentries.values():
            entity_id = subentry.data.get(CONF_COVER_ENTITY)
            if entity_id and entity_id not in state.cover_states:
                state.cover_states[entity_id] = CoverTrackingState(in_no_sun=True)
        LOGGER.debug(
            "Sun below horizon at startup for group '%s': initialized %d cover(s) with in_no_sun=True",
            entry.title,
            len(entry.subentries),
        )

    # Create async callback for applying cover tilts
    async def apply_cover_tilts() -> None:
        """Apply cover tilts based on current calculation."""
        # Check if auto control is enabled before applying to covers
        if not entry.runtime_data.auto_control_enabled:
            LOGGER.debug(
                "Auto control disabled for group '%s', skipping cover update",
                entry.title,
            )
            return

        # Get the calculation result (may be None when sun is below horizon)
        calculation = coordinator.data

        # Apply to covers — each pipe in the pipeline manages its own state
        controller = _create_controller(hass, entry)
        results = await controller.apply_to_all_covers(
            entry.subentries,
            calculation,
        )

        applied_count = sum(1 for applied in results.values() if applied)

        LOGGER.debug(
            "Sun state change: applied tilt to %d/%d covers in group '%s'",
            applied_count,
            len(results),
            entry.title,
        )

    # Store closure on runtime data for switch re-enable
    entry.runtime_data.apply_cover_tilts = apply_cover_tilts

    # Create sync callback wrapper for sun state changes
    def on_sun_state_change() -> None:
        """Handle sun state change: update coordinator and schedule cover tilt application."""
        # Update coordinator data (this updates sensors)
        coordinator.trigger_update()

        # Schedule async cover tilt application
        hass.async_create_task(apply_cover_tilts())

    # Set up sun state listener for event-driven updates
    tracked_entities = sun_provider.get_tracked_entities()
    sun_listener = SunStateListener(
        hass=hass,
        entity_ids=tracked_entities,
        update_callback=on_sun_state_change,
        debounce_seconds=1.0,
    )
    sun_listener.start()

    # Store cleanup callback
    entry.async_on_unload(sun_listener.stop)

    # Reset exit_paused for all covers at midnight so each day starts clean.
    # This prevents permanent deadlocks where exit_paused=True blocks NoSunPipe
    # from clearing itself when the sun leaves the facade late in the afternoon.
    async def _reset_exit_paused_at_midnight(_now: object) -> None:
        state = entry.runtime_data.state
        flagged = [eid for eid, s in state.cover_states.items() if s.exit_paused]
        state.reset_exit_paused()
        if flagged:
            LOGGER.debug(
                "Midnight reset: cleared exit_paused for %d cover(s) in group '%s': %s",
                len(flagged),
                entry.title,
                flagged,
            )

    entry.async_on_unload(async_track_time_change(hass, _reset_exit_paused_at_midnight, hour=0, minute=0, second=0))

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up reload listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    LOGGER.info(
        "Set up window group '%s' with %d covers",
        entry.title,
        len(entry.subentries),
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: SmartVenetianBlindsConfigEntry,
) -> bool:
    """
    Unload a config entry.

    This is called when the integration is being removed or reloaded.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: SmartVenetianBlindsConfigEntry,
) -> None:
    """
    Reload config entry.

    This is called when the integration configuration or options have changed.
    """
    await hass.config_entries.async_reload(entry.entry_id)
