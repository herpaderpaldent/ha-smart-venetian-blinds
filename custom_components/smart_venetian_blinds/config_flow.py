"""
Config flow for smart_venetian_blinds.

This module provides backwards compatibility for hassfest.
The actual implementation is in the config_flow_handler package.
"""

from __future__ import annotations

from .config_flow_handler import SmartVenetianBlindsConfigFlowHandler

__all__ = ["SmartVenetianBlindsConfigFlowHandler"]
