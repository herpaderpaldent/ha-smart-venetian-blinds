"""
Validators for config flow inputs.

This package contains validation functions for user inputs across all flow types.
"""

from __future__ import annotations

from custom_components.smart_venetian_blinds.config_flow_handler.validators.sanitizers import sanitize_name

__all__ = [
    "sanitize_name",
]
