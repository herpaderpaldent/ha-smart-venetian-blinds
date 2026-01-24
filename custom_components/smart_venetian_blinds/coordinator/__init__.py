"""
Data update coordinator package for smart_venetian_blinds.

This package provides the coordinator infrastructure for managing
sun-position-driven updates and distributing them to all entities.

Package structure:
- base.py: Main coordinator class (SmartVenetianBlindsDataUpdateCoordinator)
- state.py: GroupState dataclass for calculation results
- listeners.py: Event listeners and entity callbacks
"""

from __future__ import annotations

from .base import SmartVenetianBlindsDataUpdateCoordinator
from .state import GroupState

__all__ = ["GroupState", "SmartVenetianBlindsDataUpdateCoordinator"]
