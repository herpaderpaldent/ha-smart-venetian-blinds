"""Service actions package for smart_venetian_blinds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import DOMAIN, LOGGER
from custom_components.smart_venetian_blinds.service_actions.apply_now import async_handle_apply_now

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

SERVICE_APPLY_NOW = "apply_now"


async def async_setup_services(hass: HomeAssistant) -> None:
    """
    Register services for the integration.

    Services are registered at component level (in async_setup) rather than
    per config entry. This ensures services are available even without config entries.
    """

    async def handle_apply_now(call: ServiceCall) -> None:
        """Handle the apply_now service call."""
        await async_handle_apply_now(hass, call)

    if not hass.services.has_service(DOMAIN, SERVICE_APPLY_NOW):
        hass.services.async_register(
            DOMAIN,
            SERVICE_APPLY_NOW,
            handle_apply_now,
        )

    LOGGER.debug("Services registered for %s", DOMAIN)


__all__ = ["async_setup_services"]
