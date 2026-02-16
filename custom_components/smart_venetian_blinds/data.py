"""Custom types for smart_venetian_blinds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .coordinator.state import GroupState

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .coordinator import SmartVenetianBlindsDataUpdateCoordinator
    from .sun import SunDataProvider


type SmartVenetianBlindsConfigEntry = ConfigEntry[SmartVenetianBlindsData]


@dataclass
class SmartVenetianBlindsData:
    """
    Runtime data for a smart_venetian_blinds config entry.

    Each config entry represents a window group with:
    - Shared sun data provider
    - Coordinator for managing updates
    - Group state for calculation results
    """

    sun_provider: SunDataProvider
    coordinator: SmartVenetianBlindsDataUpdateCoordinator
    integration: Integration
    state: GroupState
    apply_cover_tilts: Callable[[], Coroutine[Any, Any, None]] | None = field(default=None, repr=False)

    @property
    def auto_control_enabled(self) -> bool:
        """Get the auto control state for this group."""
        return self.state.auto_control_enabled

    @auto_control_enabled.setter
    def auto_control_enabled(self, value: bool) -> None:
        """Set the auto control state for this group."""
        self.state.auto_control_enabled = value
