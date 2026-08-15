"""Shared entity plumbing for the Vestel TV integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity import Entity

from .api import VestelDescription, VestelTV
from .const import DOMAIN


def build_device_info(
    entry: ConfigEntry, description: VestelDescription | None
) -> DeviceInfo:
    """Describe the TV for the device registry.

    Everything here comes from the TV's own ``dd.xml``. ``manufacturer`` is
    Vestel because that is who built the panel, while ``model`` leads with the
    retail brand it was actually sold under -- these sets ship as ESSENTIELB,
    Toshiba, Finlux and others, and users recognise that name, not "Vestel".
    """
    host = entry.data[CONF_HOST]
    info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="Vestel",
        configuration_url=f"http://{host}",
    )

    if description is None:
        info["name"] = entry.title
        return info

    info["name"] = entry.title or description.name

    # e.g. "ESSENTIELB Vestel_MB211" -- brand first, then the chassis.
    model_parts = [part for part in (description.brand, description.model_name) if part]
    if model_parts:
        info["model"] = " ".join(model_parts)

    if description.software_version:
        info["sw_version"] = description.software_version
    if description.tv_version:
        info["hw_version"] = description.tv_version
    if description.mac:
        # Surfaces the MAC on the device page and lets Home Assistant tie the
        # TV to its DHCP/router entries.
        info["connections"] = {(CONNECTION_NETWORK_MAC, description.mac)}

    return info


class VestelEntity(Entity):
    """Base for entities belonging to one TV."""

    _attr_has_entity_name = True

    def __init__(
        self,
        tv: VestelTV,
        entry: ConfigEntry,
        description: VestelDescription | None,
    ) -> None:
        self._tv = tv
        self._entry = entry
        self._description = description
        self._attr_device_info = build_device_info(entry, description)
