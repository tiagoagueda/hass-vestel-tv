"""Shared entity plumbing for the Vestel TV integration."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
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
    # Collected as keyword arguments and passed to DeviceInfo once: since HA
    # 2026.11 DeviceInfo is a dataclass, and item assignment (info["x"] = ...)
    # only survives as a compatibility layer slated for removal. Keyword
    # construction works on both the dataclass and the older TypedDict.
    fields: dict[str, Any] = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "manufacturer": "Vestel",
        "configuration_url": f"http://{host}",
    }

    if description is None:
        return DeviceInfo(name=entry.title, **fields)

    fields["name"] = entry.title or description.name

    # e.g. "ESSENTIELB Vestel_MB211" -- brand first, then the chassis.
    model_parts = [part for part in (description.brand, description.model_name) if part]
    if model_parts:
        fields["model"] = " ".join(model_parts)

    if description.software_version:
        fields["sw_version"] = description.software_version
    if description.tv_version:
        fields["hw_version"] = description.tv_version
    # Home Assistant merges devices across integrations when *any* connection
    # or identifier matches, so report every MAC the TV is known by. A set with
    # both wired and wireless interfaces answers on one and advertises the
    # other, and registering only one silently prevents grouping with whichever
    # integration -- router, DHCP, device tracker -- knows it by the other.
    # format_mac is applied here because the registry rejects a stored
    # connection whose MAC is not already normalised.
    if macs := description.macs:
        fields["connections"] = {
            (CONNECTION_NETWORK_MAC, format_mac(mac)) for mac in macs
        }

    return DeviceInfo(**fields)


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
