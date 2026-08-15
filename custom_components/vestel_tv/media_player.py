"""Vestel TV media player entity."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VestelRuntime
from .const import (
    CONF_SOURCES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SOURCES,
    DOMAIN,
    KEY_PAUSE,
    KEY_PLAY,
    KEY_PROG_DOWN,
    KEY_PROG_UP,
    KEY_STOP,
    KEYS_DIGIT,
)
from .entity import VestelEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

SUPPORT_FLAGS = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.PLAY_MEDIA
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the media player from a config entry."""
    runtime: VestelRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [VestelTVMediaPlayer(runtime.tv, entry, runtime.description)],
        update_before_add=True,
    )


class VestelTVMediaPlayer(VestelEntity, MediaPlayerEntity):
    """Representation of a Vestel TV."""

    _attr_supported_features = SUPPORT_FLAGS
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.TV

    def __init__(self, tv, entry: ConfigEntry, description) -> None:
        super().__init__(tv, entry, description)
        self._sources: list[str] = list(
            entry.options.get(CONF_SOURCES, entry.data.get(CONF_SOURCES))
            or DEFAULT_SOURCES
        )
        self._attr_unique_id = entry.entry_id

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

    @property
    def media_title(self) -> str | None:
        """Whatever the TV says it is showing.

        The TV reports an app/state name such as ``PLAYER_PORTAL`` rather than
        a programme title; it is the only "now playing" hint available.
        """
        if not self._tv.state:
            return None
        return self._tv.program or self._tv.source

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Detail that has no standard media_player property of its own."""
        attributes: dict[str, Any] = {
            "host": self._tv.host,
            "discovered": self._tv.discovered,
            "websocket_connected": self._tv.ws_connected,
        }
        if self._tv.channels:
            attributes["channel_count"] = len(self._tv.channels)
            attributes["channels"] = self._tv.channels
        if (description := self._description) is not None:
            if description.brand:
                attributes["brand"] = description.brand
            if description.model_name:
                attributes["model"] = description.model_name
            if description.software_version:
                attributes["software_version"] = description.software_version
            if description.tv_version:
                attributes["tv_version"] = description.tv_version
            if description.mac:
                attributes["mac_address"] = description.mac
            if len(description.macs) > 1:
                attributes["mac_addresses"] = list(description.macs)
            if description.dial_version:
                attributes["dial_version"] = description.dial_version
        return attributes

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
        # The TV only offers a mute toggle, not an explicit set.
        await self._tv.async_toggle_mute()

    async def async_media_play(self) -> None:
        await self._tv.async_send_key(KEY_PLAY)

    async def async_media_pause(self) -> None:
        await self._tv.async_send_key(KEY_PAUSE)

    async def async_media_stop(self) -> None:
        await self._tv.async_send_key(KEY_STOP)

    async def async_media_next_track(self) -> None:
        """Channel up. Vestel has no 'next track' outside a player."""
        await self._tv.async_send_key(KEY_PROG_UP)

    async def async_media_previous_track(self) -> None:
        """Channel down."""
        await self._tv.async_send_key(KEY_PROG_DOWN)

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        """Tune to a channel number, or open a URL in the TV's browser.

        ``channel`` types the digits on the remote, since the protocol has no
        direct tune command. ``url`` uses the same call the official app makes
        to launch portal apps.
        """
        if media_type in (MediaType.CHANNEL, "channel"):
            if not media_id.isdigit():
                _LOGGER.error("Channel must be a number, got %r", media_id)
                return
            for digit in media_id:
                await self._tv.async_send_key(KEYS_DIGIT[digit])
            return

        if media_type in (MediaType.URL, "url"):
            await self._tv.async_load_url(media_id)
            return

        _LOGGER.error(
            "Unsupported media type %r; use 'channel' or 'url'", media_type
        )

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
