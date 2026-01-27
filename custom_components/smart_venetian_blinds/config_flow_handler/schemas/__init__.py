"""
Data schemas for config flow forms.

This package contains all voluptuous schemas used in config flows, options flows,
and subentry flows.

Package structure:
-----------------
- group.py: Window group configuration schemas
- cover_subentry.py: Cover subentry schemas
- options.py: Options flow schemas
"""

from __future__ import annotations

from custom_components.smart_venetian_blinds.config_flow_handler.schemas.cover_subentry import (
    get_cover_reconfigure_schema,
    get_cover_subentry_schema,
    get_cover_tilt_schema,
    get_no_sun_position_schema,
    get_protection_schema,
)
from custom_components.smart_venetian_blinds.config_flow_handler.schemas.group import (
    get_group_reconfigure_schema,
    get_group_schema,
)
from custom_components.smart_venetian_blinds.config_flow_handler.schemas.options import get_options_schema

__all__ = [
    "get_cover_reconfigure_schema",
    "get_cover_subentry_schema",
    "get_cover_tilt_schema",
    "get_group_reconfigure_schema",
    "get_group_schema",
    "get_no_sun_position_schema",
    "get_options_schema",
    "get_protection_schema",
]
