"""
Subentry flow for cover configuration.

This module implements the subentry flow for adding and modifying
covers within a window group. Each cover can have its own drive position,
tilt settings, and behavior configuration.

The flow uses a multi-step wizard:
1. Cover & Tilt Settings (user/reconfigure)
2. Protection Options (protection/reconfigure_protection)

For more information:
https://developers.home-assistant.io/docs/config_entries_config_flow_handler#subentry-flows
"""

from __future__ import annotations

from typing import Any

from custom_components.smart_venetian_blinds.config_flow_handler.schemas import (
    get_cover_tilt_schema,
    get_protection_schema,
)
from custom_components.smart_venetian_blinds.const import CONF_COVER_ENTITY, CONF_COVER_NAME, LOGGER
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers import entity_registry as er


class CoverSubentryFlowHandler(ConfigSubentryFlow):
    """
    Handle subentry flow for adding and modifying covers.

    This flow allows users to add individual covers to a window group
    and configure their specific settings like drive position, tilt angles,
    and behavior when sun is behind the facade.

    The flow is structured as a multi-step wizard:
    - Step 1: Cover entity, tilt settings
    - Step 2: Protection options (reflection protection, manual close)
    """

    _user_data: dict[str, Any]

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """
        Step 1: Cover entity and tilt settings.

        Args:
            user_input: The user input from the form.

        Returns:
            SubentryFlowResult showing form or proceeding to next step.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            cover_entity_id = user_input[CONF_COVER_ENTITY]

            # Check if cover is already added to this group
            config_entry = self._get_entry()
            for subentry in config_entry.subentries.values():
                if subentry.data.get(CONF_COVER_ENTITY) == cover_entity_id:
                    errors["base"] = "cover_already_added"
                    break

            if not errors:
                # Store data for subsequent steps
                self._user_data = user_input

                return await self.async_step_protection()

        return self.async_show_form(
            step_id="user",
            data_schema=get_cover_tilt_schema(user_input),
            errors=errors,
        )

    async def async_step_protection(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """
        Step 2: Protection options.

        Args:
            user_input: The user input from the form.

        Returns:
            SubentryFlowResult showing form or creating subentry.
        """
        if user_input is not None:
            # Merge all data from previous steps
            full_data = {**self._user_data, **user_input}

            cover_entity_id = full_data[CONF_COVER_ENTITY]
            title = self._get_cover_title(cover_entity_id, full_data)

            config_entry = self._get_entry()
            LOGGER.debug(
                "Adding cover %s to group %s",
                cover_entity_id,
                config_entry.title,
            )

            return self.async_create_entry(
                title=title,
                data=full_data,
            )

        return self.async_show_form(
            step_id="protection",
            data_schema=get_protection_schema(self._user_data),
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """
        Reconfigure Step 1: Tilt settings.

        Args:
            user_input: The user input from the form.

        Returns:
            SubentryFlowResult showing form or proceeding to next step.
        """
        config_subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            # Store data for subsequent steps, preserving cover entity ID
            self._user_data = {
                CONF_COVER_ENTITY: config_subentry.data[CONF_COVER_ENTITY],
                **user_input,
            }

            return await self.async_step_reconfigure_protection()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=get_cover_tilt_schema(config_subentry.data, show_entity_selector=False),
        )

    async def async_step_reconfigure_protection(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """
        Reconfigure Step 2: Protection options.

        Args:
            user_input: The user input from the form.

        Returns:
            SubentryFlowResult showing form or updating subentry.
        """
        config_subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            # Merge all data from previous steps
            full_data = {**self._user_data, **user_input}

            # Get updated title
            title = self._get_cover_title(
                config_subentry.data[CONF_COVER_ENTITY],
                full_data,
            )

            LOGGER.debug(
                "Reconfiguring cover %s",
                config_subentry.data[CONF_COVER_ENTITY],
            )

            # Update the subentry via config entries manager
            config_entry = self._get_entry()
            self.hass.config_entries.async_update_subentry(
                config_entry,
                config_subentry,
                title=title,
                data=full_data,
            )

            return self.async_abort(reason="reconfigure_successful")

        # Use existing values as defaults
        defaults = {**self._user_data, **config_subentry.data}

        return self.async_show_form(
            step_id="reconfigure_protection",
            data_schema=get_protection_schema(defaults),
        )

    def _get_cover_title(
        self,
        cover_entity_id: str,
        user_input: dict[str, Any],
    ) -> str:
        """
        Get a friendly title for the cover subentry.

        Uses custom name if provided, otherwise derives from entity name.

        Args:
            cover_entity_id: The cover entity ID.
            user_input: User input that may contain a custom name.

        Returns:
            A friendly title for the subentry.
        """
        # Use custom name if provided
        custom_name = user_input.get(CONF_COVER_NAME, "").strip()
        if custom_name:
            return custom_name

        # Try to get name from entity registry
        ent_reg = er.async_get(self.hass)
        entity_entry = ent_reg.async_get(cover_entity_id)
        if entity_entry and entity_entry.name:
            return entity_entry.name

        # Fall back to entity ID
        return cover_entity_id.rsplit(".", maxsplit=1)[-1].replace("_", " ").title()


__all__ = ["CoverSubentryFlowHandler"]
