"""The Vestel TV integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VestelTV
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vestel TV from a config entry."""
    session = async_get_clientsession(hass)
    tv = VestelTV(host=entry.data[CONF_HOST], session=session)
    await tv.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = tv

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        tv: VestelTV = hass.data[DOMAIN].pop(entry.entry_id)
        await tv.async_stop()
    return unloaded
