"""
Options flow for smart_venetian_blinds.

This module implements the options flow that allows users to modify settings
after the initial configuration: update throttling and the seasonal pause that
suspends cover control outside a configured part of the year.

For more information:
https://developers.home-assistant.io/docs/config_entries_options_flow_handler
"""

from __future__ import annotations

from typing import Any

from custom_components.smart_venetian_blinds.config_flow_handler.schemas import get_options_schema, get_season_schema
from custom_components.smart_venetian_blinds.config_flow_handler.validators import normalize_season_input
from custom_components.smart_venetian_blinds.season import SeasonWindow
from homeassistant import config_entries


class SmartVenetianBlindsOptionsFlow(config_entries.OptionsFlow):
    """
    Handle options flow for the integration.

    This class manages the options that users can modify after initial setup.
    The flow starts with a menu offering two areas:

    - ``timing``: update throttling, position timeout and settling delay
    - ``season``: the seasonal pause window and its rest position

    Each step merges its input into the existing options so saving one area
    never discards the other.

    For more information:
    https://developers.home-assistant.io/docs/config_entries_options_flow_handler
    """

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Show the options menu.

        Args:
            user_input: Unused, present for signature compatibility.

        Returns:
            The config flow result showing the options menu.
        """
        return self.async_show_menu(step_id="init", menu_options=["timing", "season"])

    async def async_step_timing(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Manage update throttling options.

        Args:
            user_input: The user input from the timing form, or None for initial display.

        Returns:
            The config flow result, either showing a form or creating an options entry.
        """
        if user_input is not None:
            return self._save(user_input)

        return self.async_show_form(
            step_id="timing",
            data_schema=get_options_schema(self.config_entry.options),
        )

    async def async_step_season(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Manage the seasonal pause window.

        Args:
            user_input: The user input from the season form, or None for initial display.

        Returns:
            The config flow result, either showing a form or creating an options entry.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized, errors = normalize_season_input(user_input)
            if not errors:
                return self._save(normalized)
            defaults = {**self.config_entry.options, **normalized}
        else:
            defaults = dict(self.config_entry.options)

        language = self.hass.config.language
        season = SeasonWindow.from_options(defaults)

        return self.async_show_form(
            step_id="season",
            data_schema=get_season_schema(defaults, language),
            errors=errors,
            description_placeholders={
                "active_window": season.format_window(language),
                "paused_window": season.format_pause(language),
            },
        )

    def _save(self, user_input: dict[str, Any]) -> config_entries.ConfigFlowResult:
        """Merge the step input into the existing options and persist them."""
        return self.async_create_entry(title="", data={**self.config_entry.options, **user_input})


__all__ = ["SmartVenetianBlindsOptionsFlow"]
