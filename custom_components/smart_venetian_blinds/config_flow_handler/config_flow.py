"""
Config flow for smart_venetian_blinds.

This module implements the main configuration flow for window groups:
- Initial user setup (create window group with facade/slat geometry)
- Reconfiguration of existing groups
- Subentry support for adding covers to a group

For more information:
https://developers.home-assistant.io/docs/config_entries_config_flow_handler
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from slugify import slugify

from custom_components.smart_venetian_blinds.config_flow_handler.schemas import (
    get_group_reconfigure_schema,
    get_group_schema,
)
from custom_components.smart_venetian_blinds.config_flow_handler.subentry_flow import CoverSubentryFlowHandler
from custom_components.smart_venetian_blinds.const import CONF_GROUP_NAME, DOMAIN, LOGGER, SUBENTRY_TYPE_COVER
from homeassistant import config_entries
from homeassistant.core import callback

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.config_flow_handler.options_flow import SmartVenetianBlindsOptionsFlow


class SmartVenetianBlindsConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for smart_venetian_blinds.

    This class manages the configuration flow for window groups, including
    initial setup, reconfiguration, and subentry support for covers.

    Supported flows:
    - user: Initial setup via UI (create window group)
    - reconfigure: Update existing group configuration

    Subentry flows:
    - cover: Add/modify covers within a window group
    """

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SmartVenetianBlindsOptionsFlow:
        """Get the options flow for this handler."""
        from custom_components.smart_venetian_blinds.config_flow_handler.options_flow import (  # noqa: PLC0415
            SmartVenetianBlindsOptionsFlow,
        )

        return SmartVenetianBlindsOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls,
        config_entry: config_entries.ConfigEntry,
    ) -> dict[str, type[config_entries.ConfigSubentryFlow]]:
        """Return subentry types supported by this integration."""
        return {
            SUBENTRY_TYPE_COVER: CoverSubentryFlowHandler,
        }

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle a flow initialized by the user.

        This creates a new window group with facade orientation and slat geometry.

        Args:
            user_input: The user input from the config flow form.

        Returns:
            The config flow result, either showing a form or creating an entry.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            group_name = user_input[CONF_GROUP_NAME].strip()

            if not group_name:
                errors["base"] = "name_required"
            else:
                # Set unique ID based on slugified group name
                unique_id = slugify(group_name)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                LOGGER.debug("Creating window group: %s", group_name)

                return self.async_create_entry(
                    title=group_name,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=get_group_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle reconfiguration of a window group.

        Allows users to update facade orientation and slat geometry.

        Args:
            user_input: The user input from the reconfigure form.

        Returns:
            The config flow result, either showing a form or updating the entry.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            # Merge with existing data (keep the name)
            new_data = {**entry.data, **user_input}

            LOGGER.debug("Reconfiguring window group: %s", entry.title)

            return self.async_update_reload_and_abort(
                entry,
                data=new_data,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=get_group_reconfigure_schema(entry.data),
            errors=errors,
        )


__all__ = ["SmartVenetianBlindsConfigFlowHandler"]
