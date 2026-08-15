"""Remote entity for a Vestel TV.

Gives every key a name for ``remote.send_command``, which is where Home
Assistant expects TV navigation to live -- the media player domain has no
concept of a D-pad, menu or colour keys.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VestelRuntime
from .const import DOMAIN, REMOTE_COMMANDS, REMOTE_TEXT_PREFIX
from .entity import VestelEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the remote entity."""
    runtime: VestelRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VestelTVRemote(runtime.tv, entry, runtime.description)])


class VestelTVRemote(VestelEntity, RemoteEntity):
    """Send arbitrary remote keys to the TV."""

    _attr_translation_key = "remote"

    def __init__(self, tv, entry: ConfigEntry, description) -> None:
        super().__init__(tv, entry, description)
        self._attr_unique_id = f"{entry.entry_id}_remote"

    @property
    def is_on(self) -> bool:
        return self._tv.state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"commands": sorted(REMOTE_COMMANDS)}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._tv.async_turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._tv.async_turn_off()

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send one or more keys.

        Each command is a name from ``REMOTE_COMMANDS``, a raw numeric key code
        for anything not named here, or ``text:some words`` to type a string.
        """
        num_repeats: int = kwargs.get(ATTR_NUM_REPEATS, 1)
        delay: float = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)

        commands = list(command)
        for _ in range(num_repeats):
            for index, single in enumerate(commands):
                await self._async_send_single(single)
                # Space out keys, but do not pad the very last one.
                if delay and index < len(commands) - 1:
                    await asyncio.sleep(delay)

    async def _async_send_single(self, command: str) -> None:
        command = command.strip()

        if command.lower().startswith(REMOTE_TEXT_PREFIX):
            text = command[len(REMOTE_TEXT_PREFIX) :]
            if text:
                await self._tv.async_send_text(text)
            return

        if (code := REMOTE_COMMANDS.get(command.lower())) is None:
            # Allow raw codes so keys we have not named are still reachable.
            if command.isdigit():
                code = int(command)
            else:
                raise ServiceValidationError(
                    f"Unknown command '{command}'. Use one of: "
                    f"{', '.join(sorted(REMOTE_COMMANDS))}; a raw numeric key "
                    f"code; or '{REMOTE_TEXT_PREFIX}some text' to type."
                )

        if not await self._tv.async_send_key(code):
            _LOGGER.warning("Command %r (key %s) was not accepted", command, code)
