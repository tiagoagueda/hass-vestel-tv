"""Vestel TV media player entity."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import VestelTV
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

SUPPORT_FLAGS = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the media player from a config entry."""
    tv: VestelTV = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VestelTVMediaPlayer(tv, entry)], update_before_add=True)


class VestelTVMediaPlayer(MediaPlayerEntity):
    """Representation of a Vestel TV."""

    _attr_supported_features = SUPPORT_FLAGS
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, tv: VestelTV, entry: ConfigEntry) -> None:
        self._tv = tv
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Vestel",
            "configuration_url": f"http://{entry.data[CONF_HOST]}",
        }

    @property
    def state(self) -> MediaPlayerState:
        return MediaPlayerState.ON if self._tv.state else MediaPlayerState.OFF

    @property
    def is_volume_muted(self) -> bool:
        return self._tv.muted

    @property
    def volume_level(self) -> float:
        return self._tv.volume / 100

    @property
    def source(self) -> str | None:
        return self._tv.source if self._tv.state else None

    async def async_update(self) -> None:
        await self._tv.async_update()

    async def async_turn_on(self) -> None:
        await self._tv.async_turn_on()

    async def async_turn_off(self) -> None:
        await self._tv.async_turn_off()

    async def async_volume_up(self) -> None:
        await self._tv.async_volume_up()

    async def async_volume_down(self) -> None:
        await self._tv.async_volume_down()

    async def async_mute_volume(self, mute: bool) -> None:
        await self._tv.async_toggle_mute()

    async def async_select_source(self, source: str) -> None:
        # Vestel has no direct-select API; cycle until source matches.
        for _ in range(10):
            if self._tv.source == source:
                return
            await self._tv.async_select_source_step()
            await self._tv.async_update()
