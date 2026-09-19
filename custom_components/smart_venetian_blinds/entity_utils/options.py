"""Helper for entities that write their value back into the config entry options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.data import SmartVenetianBlindsConfigEntry
    from homeassistant.core import HomeAssistant


def async_merge_entry_options(
    hass: HomeAssistant,
    entry: SmartVenetianBlindsConfigEntry,
    **changes: Any,
) -> None:
    """
    Merge values into a config entry's options.

    Updating the entry fires its update listener, which reloads the entry so the
    new settings take effect everywhere, including the options flow form.

    Args:
        hass: The Home Assistant instance.
        entry: The window group config entry.
        changes: Option keys to set.
    """
    hass.config_entries.async_update_entry(entry, options={**entry.options, **changes})
