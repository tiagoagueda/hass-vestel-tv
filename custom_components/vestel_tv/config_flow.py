"""Config flow for Vestel TV."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac

from .api import VestelDescription, async_fetch_description, async_probe_description
from .const import DEFAULT_NAME, DOMAIN

if TYPE_CHECKING:
    # Home Assistant moved the SSDP service-info dataclass out of the component
    # and into helpers. Only the annotation needs it, so importing it lazily
    # keeps this working either side of that move.
    from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


class VestelTVConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vestel TV."""

    VERSION = 2

    def __init__(self) -> None:
        self._host: str | None = None
        self._description: VestelDescription | None = None

    def _unique_id_for(self, description: VestelDescription, host: str) -> str:
        """Key the entry by MAC where possible, falling back to the host.

        Vestel's own app keys its device table by MAC for good reason: a TV
        that picks up a new DHCP lease is still the same TV. Falling back to
        the host keeps sets that do not publish a MAC working, at the cost of
        reappearing as a new device if their address changes.
        """
        if description.mac:
            return format_mac(description.mac)
        return host

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a manually entered TV."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            session = async_get_clientsession(self.hass)
            description = await async_probe_description(session, host)

            if description is None:
                errors["base"] = "cannot_connect"
            elif not description.is_vestel:
                errors["base"] = "not_vestel"
            else:
                await self.async_set_unique_id(self._unique_id_for(description, host))
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or description.name,
                    data={CONF_HOST: host, CONF_NAME: user_input.get(CONF_NAME)},
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_ssdp(
        self, discovery_info: SsdpServiceInfo
    ) -> ConfigFlowResult:
        """Handle a TV found over SSDP.

        Every DIAL device answers the search target this integration registers,
        so most callers here are not Vestels and get turned away.
        """
        location = discovery_info.ssdp_location
        if not location:
            return self.async_abort(reason="not_vestel")

        host = urlparse(location).hostname
        if not host:
            return self.async_abort(reason="not_vestel")

        session = async_get_clientsession(self.hass)
        description = await async_fetch_description(session, location)
        if description is None or not description.is_vestel:
            return self.async_abort(reason="not_vestel")

        await self.async_set_unique_id(self._unique_id_for(description, host))
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        # Entries created before MAC-keying, or added by hand, are keyed by
        # host; without this a rediscovered TV would be offered a second time.
        self._async_abort_entries_match({CONF_HOST: host})

        self._host = host
        self._description = description
        self.context["title_placeholders"] = {"name": description.name}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to confirm adding a discovered TV."""
        assert self._host is not None
        assert self._description is not None

        if user_input is not None:
            return self.async_create_entry(
                title=self._description.name,
                data={CONF_HOST: self._host, CONF_NAME: self._description.name},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "name": self._description.name,
                "host": self._host,
                "model": self._description.model_name or "unknown",
            },
        )
