"""Async client for Vestel TV sets.

Ported and modernized from T3m3z/pyvesteltv (MIT). Combines:
  * DIAL/SSDP discovery -> Application-URL for HTTP key codes
  * HTTP POST /vr/remote with XML body for sending key codes
  * TCP socket on :1986 for state queries (GETMUTE, GETSOURCE, ...)
  * WebSocket on :7681 for state broadcasts (best-effort, optional)
"""
from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any, Callable
from xml.etree import ElementTree

import aiohttp

from .const import (
    DEFAULT_PORT_TCP,
    DEFAULT_PORT_WS,
    DEFAULT_TIMEOUT,
    KEY_MUTE,
    KEY_POWER,
    KEY_SOURCE,
    KEY_VOL_DOWN,
    KEY_VOL_UP,
)

_LOGGER = logging.getLogger(__name__)

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_ST = "urn:dial-multiscreen-org:service:dial:1"
DISCOVERY_INTERVAL = 5
DISCOVERY_TIMEOUT = 16

_SSDP_MSEARCH = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 1\r\n"
    f"ST: {SSDP_ST}\r\n\r\n"
).encode()


class _DialDiscovery(asyncio.DatagramProtocol):
    """SSDP listener that resolves a Vestel TV's DIAL Application-URL."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self._host = host
        self._session = session
        self._app_url: str | None = None
        self._last_seen: float = 0.0
        self._transport: asyncio.DatagramTransport | None = None
        self._broadcast_task: asyncio.Task | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = transport  # type: ignore[assignment]
        self._broadcast_task = asyncio.get_running_loop().create_task(self._broadcast_loop())

    def connection_lost(self, exc: Exception | None) -> None:
        if self._broadcast_task:
            self._broadcast_task.cancel()

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if addr[0] != self._host:
            return
        for line in data.decode(errors="ignore").split("\r\n"):
            if line.upper().startswith("LOCATION:"):
                location = line.split(":", 1)[1].strip()
                asyncio.get_running_loop().create_task(self._resolve(location))
                return

    async def _broadcast_loop(self) -> None:
        try:
            while True:
                if self._transport:
                    self._transport.sendto(_SSDP_MSEARCH, (SSDP_ADDR, SSDP_PORT))
                await asyncio.sleep(DISCOVERY_INTERVAL)
        except asyncio.CancelledError:
            pass

    async def _resolve(self, location: str) -> None:
        try:
            async with self._session.get(location, timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as resp:
                self._app_url = resp.headers.get("Application-URL")
                if self._app_url and not self._app_url.endswith("/"):
                    self._app_url += "/"
                self._last_seen = monotonic()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("DIAL resolve failed for %s: %s", location, err)

    @property
    def discovered(self) -> bool:
        return monotonic() - self._last_seen < DISCOVERY_TIMEOUT

    @property
    def app_url(self) -> str | None:
        return self._app_url if self.discovered else None

    def close(self) -> None:
        if self._transport:
            self._transport.close()


class VestelTV:
    """Async Vestel TV client."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        tcp_port: int = DEFAULT_PORT_TCP,
        ws_port: int = DEFAULT_PORT_WS,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._host = host
        self._session = session
        self._tcp_port = tcp_port
        self._ws_port = ws_port
        self._timeout = timeout

        self._discovery: _DialDiscovery | None = None

        self.state: bool = False
        self.muted: bool = False
        self.volume: int = 0
        self.source: str = "Unknown"
        self.program: str = "Unknown"

    @property
    def host(self) -> str:
        return self._host

    @property
    def discovered(self) -> bool:
        return self._discovery is not None and self._discovery.discovered

    async def async_start(self) -> None:
        """Begin SSDP discovery."""
        if self._discovery is not None:
            return
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: _DialDiscovery(self._host, self._session),
            local_addr=("0.0.0.0", 0),
            allow_broadcast=True,
        )
        self._discovery = protocol  # type: ignore[assignment]

    async def async_stop(self) -> None:
        if self._discovery:
            self._discovery.close()
            self._discovery = None

    async def async_send_key(self, code: int) -> None:
        """POST a key code to /vr/remote on the discovered Application-URL."""
        url = self._discovery.app_url if self._discovery else None
        if not url:
            _LOGGER.debug("send_key skipped: TV not discovered")
            return
        body = f'<?xml version="1.0" ?><remote><key code="{code}"/></remote>'
        try:
            async with self._session.post(
                f"{url}vr/remote",
                data=body,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as _:
                pass
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("send_key %s failed: %s", code, err)

    async def async_turn_on(self) -> None:
        if not self.state:
            await self.async_send_key(KEY_POWER)

    async def async_turn_off(self) -> None:
        if self.state:
            await self.async_send_key(KEY_POWER)

    async def async_volume_up(self) -> None:
        await self.async_send_key(KEY_VOL_UP)

    async def async_volume_down(self) -> None:
        await self.async_send_key(KEY_VOL_DOWN)

    async def async_toggle_mute(self) -> None:
        await self.async_send_key(KEY_MUTE)

    async def async_select_source_step(self) -> None:
        """Cycle to the next source. Vestel has no direct-select; UI cycles."""
        await self.async_send_key(KEY_SOURCE)

    async def async_update(self) -> None:
        """Poll TV state via TCP queries."""
        if not self.discovered:
            self.state = False
            return
        try:
            await asyncio.wait_for(self._read_tcp(), timeout=self._timeout)
            self.state = True
        except (OSError, asyncio.TimeoutError) as err:
            _LOGGER.debug("TCP read failed (TV likely off): %s", err)
            self.state = False

    async def _read_tcp(self) -> None:
        reader, writer = await asyncio.open_connection(self._host, self._tcp_port)
        try:
            self.muted = await self._query(reader, writer, "GETMUTE", lambda v: v == "ON")
            self.source = await self._query(reader, writer, "GETSOURCE", str)
            self.program = await self._query(reader, writer, "GETPROGRAM", str)
            self.volume = await self._query(reader, writer, "GETHEADPHONEVOLUME", int)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass

    @staticmethod
    async def _query(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        command: str,
        cast: Callable[[str], Any],
    ) -> Any:
        writer.write(f"{command}\r\n".encode())
        await writer.drain()
        raw = (await reader.readline()).decode(errors="ignore").strip()
        value = raw.split(" is ")[-1] if " is " in raw else raw.split(" ")[-1]
        return cast(value)
