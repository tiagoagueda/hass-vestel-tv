"""Remote-key buttons for a Vestel TV.

One button per navigation/utility key, so they can be put on a dashboard or
called from an automation without knowing the numeric key codes.
"""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VestelRuntime
from .const import DOMAIN, REMOTE_BUTTONS
from .entity import VestelEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one button per remote key."""
    runtime: VestelRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        VestelTVButton(runtime.tv, entry, runtime.description, key, code)
        for key, code in REMOTE_BUTTONS
    )


class VestelTVButton(VestelEntity, ButtonEntity):
    """A single remote key, exposed as a button."""

    def __init__(self, tv, entry, description, key: str, code: int) -> None:
        super().__init__(tv, entry, description)
        self._code = code
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        return {"key_code": self._code}

    async def async_press(self) -> None:
        """Send the key code to the TV."""
        if not await self._tv.async_send_key(self._code):
            _LOGGER.warning(
                "Key %s (%s) was not accepted by the TV",
                self._attr_translation_key,
                self._code,
            )
