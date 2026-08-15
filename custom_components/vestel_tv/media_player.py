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
from .const import CONF_SOURCES, DEFAULT_SCAN_INTERVAL, DEFAULT_SOURCES, DOMAIN

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
        self._sources: list[str] = list(
            entry.options.get(CONF_SOURCES, entry.data.get(CONF_SOURCES))
            or DEFAULT_SOURCES
        )
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
    def volume_level(self) -> float | None:
        # The TV reports no readable volume level over this protocol, only
        # relative steps, so leave it unknown rather than inventing a number.
        if self._tv.volume is None:
            return None
        return self._tv.volume / 100

    @property
    def source(self) -> str | None:
        return self._tv.source if self._tv.state else None

    @property
    def source_list(self) -> list[str]:
        return self._sources

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
        # Vestel has no direct-select API; the source key cycles the input.
        if self._tv.source is None:
            # Without a readable current source there is nothing to compare
            # against, so cycling would fire the key blindly. Step once.
            _LOGGER.debug(
                "Current source unknown; sending a single source step instead "
                "of cycling towards %s",
                source,
            )
            await self._tv.async_select_source_step()
            return
        for _ in range(10):
            if self._tv.source == source:
                return
            await self._tv.async_select_source_step()
            await self._tv.async_update()
        _LOGGER.warning("Gave up cycling to source %s", source)
