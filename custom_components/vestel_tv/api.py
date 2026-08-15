"""Async client for Vestel TV sets.

Speaks the protocol used by Vestel's own "TV Smart Centre" app, recovered by
capturing that app against a Vestel_MB211 (software 3.33.21.0):

  * SSDP/DIAL discovery -> Application-URL, the base for everything else
  * Commands POST to the DIAL app endpoint ``{app_url}SmartCenter`` as XML,
    answered with ``201 Created``
  * State arrives on a WebSocket at ``ws://host:7681/`` -- which stays silent
    unless the handshake carries an ``Origin`` header

This replaces the older pyvesteltv-derived design (key codes to ``vr/remote``,
state over TCP 1986). Neither of those exists on MB211-era firmware: ``vr/remote``
returns 404 and 1986 is absent from all 65535 ports, with or without the TV's
"Virtual Remote" setting enabled.

Keep Home Assistant imports out of this module -- it must stay a plain async
client.
"""
from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass
from time import monotonic
from xml.etree import ElementTree

import aiohttp

from .const import (
    APP_NAME_HEADER,
    APP_NAME_VALUE,
    CONTENT_TYPE,
    DEFAULT_NAME,
    DEFAULT_PORT_WS,
    DEFAULT_TIMEOUT,
    DESCRIPTION_PORTS,
    KEY_MUTE,
    KEY_POWER,
    KEY_SOURCE,
    KEY_VOL_DOWN,
    KEY_VOL_UP,
    PAYLOAD_ENCODING,
    SMARTCENTER_APP,
)

_LOGGER = logging.getLogger(__name__)

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_ST = "urn:dial-multiscreen-org:service:dial:1"
SSDP_TTL = 2
DISCOVERY_INTERVAL = 5
DISCOVERY_TIMEOUT = 16

WS_RECONNECT_DELAY = 10
TEXT_KEY_DELAY = 0.15

_SSDP_MSEARCH = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 1\r\n"
    f"ST: {SSDP_ST}\r\n\r\n"
).encode()


@dataclass(frozen=True)
class VestelDescription:
    """Parsed DIAL device description (``dd.xml``) for one TV."""

    location: str
    app_url: str | None = None
    friendly_name: str | None = None
    model_name: str | None = None
    tv_version: str | None = None
    software_version: str | None = None
    dial_version: str | None = None
    verification_key: str | None = None
    mac: str | None = None

    @property
    def is_vestel(self) -> bool:
        """Whether this description came from a Vestel TV.

        Every DIAL device on the network answers the same search target --
        Chromecasts, streaming sticks, other TVs -- so a reply alone proves
        nothing. Vestel's own app filters these by looking for the custom
        fields Vestel adds to ``dd.xml`` ("non-smartcenter UPnP device msearch
        is masked"); this mirrors that check.
        """
        if self.verification_key or self.tv_version:
            return True
        return bool(self.model_name and "vestel" in self.model_name.lower())

    @property
    def name(self) -> str:
        """A human-friendly name for the config flow.

        Vestel sets report a ``friendlyName`` of ``BRAND_aa:bb:cc:dd:ee:ff``,
        which is no one's idea of a device name, so drop the MAC suffix.
        """
        friendly = (self.friendly_name or "").strip()
        brand, separator, suffix = friendly.rpartition("_")
        if separator and suffix.count(":") == 5:
            friendly = brand
        return friendly or self.model_name or DEFAULT_NAME


def _local_name(tag: str) -> str:
    """Strip any XML namespace from *tag*."""
    return tag.rpartition("}")[2]


def _parse_description(location: str, app_url: str | None, xml: str) -> VestelDescription:
    """Build a :class:`VestelDescription` from a ``dd.xml`` body.

    Vestel's extra fields live in a ``<locale>`` block alongside the standard
    UPnP device element, so this flattens the whole tree by local tag name
    rather than walking a fixed path.
    """
    values: dict[str, str] = {}
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as err:
        _LOGGER.debug("Could not parse device description at %s: %s", location, err)
        return VestelDescription(location=location, app_url=app_url)
    for element in root.iter():
        text = (element.text or "").strip()
        if text:
            values.setdefault(_local_name(element.tag), text)
    return VestelDescription(
        location=location,
        app_url=app_url,
        friendly_name=values.get("friendlyName"),
        model_name=values.get("modelName"),
        tv_version=values.get("tv_version"),
        software_version=values.get("software_version"),
        dial_version=values.get("dial_version"),
        verification_key=values.get("verificationKey"),
        mac=values.get("mac"),
    )


async def async_fetch_description(
    session: aiohttp.ClientSession,
    location: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> VestelDescription | None:
    """Fetch and parse a DIAL description document."""
    try:
        async with session.get(
            location, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status != 200:
                return None
            app_url = resp.headers.get("Application-URL")
            if app_url and not app_url.endswith("/"):
                app_url += "/"
            return _parse_description(location, app_url, await resp.text())
    except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeDecodeError) as err:
        _LOGGER.debug("Description fetch failed for %s: %s", location, err)
        return None


async def async_probe_description(
    session: aiohttp.ClientSession,
    host: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> VestelDescription | None:
    """Look for a TV's description on *host* without waiting for SSDP.

    SSDP is authoritative but takes a broadcast round to answer, which is a
    long time to hold a config-flow form. The description usually sits on a
    well-known port, so try those first; callers fall back to discovery.
    """
    for port in DESCRIPTION_PORTS:
        description = await async_fetch_description(
            session, f"http://{host}:{port}/dd.xml", timeout
        )
        if description is not None:
            return description
    return None


def _source_address_for(host: str) -> str | None:
    """Return the local IPv4 address the OS would use to reach *host*.

    Connecting a UDP socket sends no packets; it only asks the routing table
    which interface applies. On a multi-homed host (Docker bridges, VPN
    adapters, hypervisor switches) this is the only reliable way to pick the
    interface that can actually see the TV.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((host, SSDP_PORT))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def _create_ssdp_socket(local_addr: str | None) -> socket.socket:
    """Build an SSDP socket with multicast pinned to *local_addr*."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP_TTL)
    if local_addr:
        # Binding alone does not decide egress; IP_MULTICAST_IF does.
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_addr)
        )
        sock.bind((local_addr, 0))
    else:
        sock.bind(("0.0.0.0", 0))
    sock.setblocking(False)
    return sock


class _DialDiscovery(asyncio.DatagramProtocol):
    """SSDP listener that resolves a Vestel TV's DIAL Application-URL."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self._host = host
        self._session = session
        self._app_url: str | None = None
        self._description: VestelDescription | None = None
        self._last_seen: float = 0.0
        self._transport: asyncio.DatagramTransport | None = None
        self._broadcast_task: asyncio.Task | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = transport  # type: ignore[assignment]
        loop = asyncio.get_running_loop()
        self._broadcast_task = loop.create_task(self._broadcast_loop())

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
        description = await async_fetch_description(self._session, location)
        if description is None:
            return
        self._description = description
        self._app_url = description.app_url
        self._last_seen = monotonic()

    @property
    def discovered(self) -> bool:
        return monotonic() - self._last_seen < DISCOVERY_TIMEOUT

    @property
    def app_url(self) -> str | None:
        return self._app_url if self.discovered else None

    @property
    def description(self) -> VestelDescription | None:
        return self._description

    def close(self) -> None:
        if self._transport:
            self._transport.close()


class VestelTV:
    """Async Vestel TV client speaking the Smart Centre protocol."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        ws_port: int = DEFAULT_PORT_WS,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._host = host
        self._session = session
        self._ws_port = ws_port
        self._timeout = timeout

        self._discovery: _DialDiscovery | None = None
        self._ws_task: asyncio.Task | None = None
        self._ws_connected = False

        self.state: bool = False
        self.muted: bool = False
        self.volume: int | None = None
        self.source: str | None = None
        self.program: str | None = None
        self.channels: list[str] = []
        self.last_ws_message: str = ""

    @property
    def host(self) -> str:
        return self._host

    @property
    def discovered(self) -> bool:
        return self._discovery is not None and self._discovery.discovered

    @property
    def app_url(self) -> str | None:
        return self._discovery.app_url if self._discovery else None

    @property
    def description(self) -> VestelDescription | None:
        """The TV's parsed dd.xml, once discovery has resolved it."""
        return self._discovery.description if self._discovery else None

    @property
    def ws_connected(self) -> bool:
        return self._ws_connected

    async def async_start(self) -> None:
        """Begin SSDP discovery and the state WebSocket."""
        if self._discovery is None:
            local_addr = _source_address_for(self._host)
            if local_addr is None:
                _LOGGER.warning(
                    "No route to %s; falling back to the default interface, which "
                    "may not reach the TV on a multi-homed host",
                    self._host,
                )
            else:
                _LOGGER.debug(
                    "SSDP discovery bound to %s for %s", local_addr, self._host
                )
            sock = _create_ssdp_socket(local_addr)
            loop = asyncio.get_running_loop()
            _, protocol = await loop.create_datagram_endpoint(
                lambda: _DialDiscovery(self._host, self._session),
                sock=sock,
            )
            self._discovery = protocol  # type: ignore[assignment]

        if self._ws_task is None:
            self._ws_task = asyncio.get_running_loop().create_task(self._ws_loop())

    async def async_stop(self) -> None:
        """Tear down the WebSocket and discovery."""
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None
        if self._discovery:
            self._discovery.close()
            self._discovery = None
        self._ws_connected = False

    # ------------------------------------------------------------------
    # Command channel: POST XML to {app_url}SmartCenter
    # ------------------------------------------------------------------

    async def _async_post(self, payload: str) -> bool:
        """POST *payload* to the SmartCenter DIAL endpoint.

        The TV answers ``201 Created`` with a Location header and an empty
        body; replies to queries arrive on the WebSocket instead.
        """
        url = self.app_url
        if not url:
            _LOGGER.debug("command skipped, TV not discovered: %s", payload)
            return False
        try:
            async with self._session.post(
                f"{url}{SMARTCENTER_APP}",
                data=payload.encode(PAYLOAD_ENCODING, errors="replace"),
                headers={
                    APP_NAME_HEADER: APP_NAME_VALUE,
                    "Content-Type": CONTENT_TYPE,
                },
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as resp:
                if resp.status not in (200, 201):
                    _LOGGER.warning(
                        "TV rejected command (HTTP %s): %s", resp.status, payload
                    )
                    return False
                return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Command failed (%s): %s", err, payload)
            return False

    async def async_send_key(self, code: int) -> bool:
        """Send a remote-control key code."""
        return await self._async_post(
            f"<?xml version='1.0' ?><remote><key code='{code}'/></remote>"
        )

    async def async_send_text(self, text: str) -> bool:
        """Type *text* on the TV, one POST per character.

        The TV takes a single character per request, as its own app does.
        """
        ok = True
        for char in text:
            ok &= await self._async_post(
                f"<?xml version='1.0' ?><keyboard><key value='{ord(char)}'/></keyboard>"
            )
            await asyncio.sleep(TEXT_KEY_DELAY)
        return ok

    async def async_send_command(self, name: str) -> bool:
        """Send a query command. Any reply arrives over the WebSocket."""
        return await self._async_post(f"<command>{name}</command>")

    async def async_load_url(self, url: str, page: str = "RC") -> bool:
        """Open *url* in the TV's portal browser (how the app launches apps)."""
        return await self._async_post(
            f"<?xml version='1.0' ?><browserseturl>"
            f"<load url='{url}' page='{page}'/></browserseturl>"
        )

    # Convenience wrappers -------------------------------------------------

    async def async_turn_on(self) -> None:
        """Send the power key.

        Power is a toggle and the TV only listens while it is on the network,
        so this can only work if the TV is still reachable. A set powered off
        with the physical remote leaves the network entirely; waking it needs
        Wake-on-LAN, which is not implemented.
        """
        if not self.state:
            await self.async_send_key(KEY_POWER)

    async def async_turn_off(self) -> None:
        await self.async_send_key(KEY_POWER)

    async def async_volume_up(self) -> None:
        await self.async_send_key(KEY_VOL_UP)

    async def async_volume_down(self) -> None:
        await self.async_send_key(KEY_VOL_DOWN)

    async def async_toggle_mute(self) -> None:
        await self.async_send_key(KEY_MUTE)

    async def async_select_source_step(self) -> None:
        """Cycle to the next source. Vestel has no direct-select."""
        await self.async_send_key(KEY_SOURCE)

    # ------------------------------------------------------------------
    # State channel: WebSocket on :7681, root path, Origin header required
    # ------------------------------------------------------------------

    async def _ws_loop(self) -> None:
        """Hold the state WebSocket open, reconnecting as needed."""
        url = f"ws://{self._host}:{self._ws_port}/"
        headers = {"Origin": f"http://{self._host}"}
        while True:
            try:
                async with self._session.ws_connect(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientWSTimeout(ws_close=self._timeout),
                ) as ws:
                    self._ws_connected = True
                    self.state = True
                    _LOGGER.debug("State WebSocket connected to %s", url)
                    async for msg in ws:
                        if msg.type is aiohttp.WSMsgType.TEXT:
                            self._handle_ws_message(msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, OSError, asyncio.TimeoutError) as err:
                # A Vestel set that is off drops off the network entirely, so a
                # failure to connect is the best available "TV is off" signal.
                _LOGGER.debug("State WebSocket unavailable (TV likely off): %s", err)
            self._ws_connected = False
            self.state = False
            await asyncio.sleep(WS_RECONNECT_DELAY)

    def _handle_ws_message(self, message: str) -> None:
        """Parse one broadcast frame from the TV."""
        message = message.strip()
        if not message:
            return
        self.last_ws_message = message
        _LOGGER.debug("WS frame: %s", message[:200])

        if message.startswith("<tv_state"):
            value = self._attr(message, "value")
            if value is not None:
                self.source = value or None
                self.state = True
            return

        if message.startswith("tv_status:"):
            self.state = message.split(":", 1)[1].strip() == "1"
            return

        if message.startswith("<active_list"):
            self._parse_channel_list(message)
            return

    def _parse_channel_list(self, message: str) -> None:
        """Pull channel names out of an <active_list> frame."""
        try:
            root = ElementTree.fromstring(message)
        except ElementTree.ParseError as err:
            _LOGGER.debug("Could not parse channel list: %s", err)
            return
        names = [
            name
            for service in root.iter("service")
            if (name := service.get("name"))
        ]
        if names:
            self.channels = names

    @staticmethod
    def _attr(message: str, attribute: str) -> str | None:
        """Read a single quoted attribute without a full XML parse.

        Some frames arrive as fragments rather than well-formed documents.
        """
        marker = f"{attribute}='"
        start = message.find(marker)
        if start == -1:
            return None
        start += len(marker)
        end = message.find("'", start)
        return message[start:end] if end != -1 else None

    async def async_update(self) -> None:
        """Ask the TV to re-broadcast its state.

        Replies land on the WebSocket, so this only nudges the TV; the entity
        reads whatever the socket has most recently reported.
        """
        if not self.discovered:
            self.state = False
            return
        if not self._ws_connected:
            # Discovery alone does not prove the TV is on -- the DIAL server
            # answers in standby too.
            return
        await self.async_send_command("tvstate")
