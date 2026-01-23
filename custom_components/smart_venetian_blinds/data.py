"""Custom types for smart_venetian_blinds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import SmartVenetianBlindsApiClient
    from .coordinator import SmartVenetianBlindsDataUpdateCoordinator


type SmartVenetianBlindsConfigEntry = ConfigEntry[SmartVenetianBlindsData]


@dataclass
class SmartVenetianBlindsData:
    """Data for smart_venetian_blinds."""

    client: SmartVenetianBlindsApiClient
    coordinator: SmartVenetianBlindsDataUpdateCoordinator
    integration: Integration
