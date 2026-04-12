"""
Data update coordinator package for smart_venetian_blinds.

Package structure:
- base.py: Main coordinator class (SmartVenetianBlindsDataUpdateCoordinator)
- state.py: GroupState dataclass for per-group throttling and calculation state
"""

from __future__ import annotations

from .base import SmartVenetianBlindsDataUpdateCoordinator
from .state import GroupState

__all__ = ["GroupState", "SmartVenetianBlindsDataUpdateCoordinator"]
