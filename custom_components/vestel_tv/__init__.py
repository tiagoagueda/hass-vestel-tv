"""The Vestel TV integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac

from .api import VestelDescription, VestelTV, async_probe_description
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.BUTTON]


@dataclass
class VestelRuntime:
    """What the platforms need: the client, plus the TV's description.

    The description is read once at setup so the device registry can be
    populated immediately, rather than waiting for an SSDP round to land.
    """

    tv: VestelTV
    description: VestelDescription | None


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate host-keyed entries (v1) to MAC-keyed entries (v2).

    Version 1 used the TV's address as the unique ID, so a new DHCP lease
    looked like a new device. If the TV answers we re-key it to its MAC;
    if it is unreachable we keep the old ID rather than fail the migration,
    and it will simply stay host-keyed.
    """
    if entry.version >= 2:
        return True

    unique_id = entry.unique_id
    session = async_get_clientsession(hass)
    description = await async_probe_description(session, entry.data[CONF_HOST])
    if description is not None and description.mac:
        unique_id = format_mac(description.mac)
        _LOGGER.debug("Migrating %s to MAC-based unique ID %s", entry.title, unique_id)
    else:
        _LOGGER.info(
            "Could not reach %s to read its MAC; keeping the address as its "
            "unique ID. Re-adding the TV later will key it by MAC",
            entry.data[CONF_HOST],
        )

    hass.config_entries.async_update_entry(entry, unique_id=unique_id, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vestel TV from a config entry."""
    session = async_get_clientsession(hass)
    host = entry.data[CONF_HOST]
    tv = VestelTV(host=host, session=session)
    await tv.async_start()

    # Best-effort: a TV that is off cannot describe itself, and that must not
    # block setup. The device registry keeps whatever it learned last time.
    description = await async_probe_description(session, host)
    if description is None:
        _LOGGER.debug("No device description from %s at setup; TV may be off", host)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = VestelRuntime(
        tv=tv, description=description
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        runtime: VestelRuntime = hass.data[DOMAIN].pop(entry.entry_id)
        await runtime.tv.async_stop()
    return unloaded
