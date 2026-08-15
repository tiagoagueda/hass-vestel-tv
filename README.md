# Vestel TV

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![Community Forum][forum-shield]][forum]

Home Assistant custom integration for Vestel-built smart TVs, controlled locally over the
TV's own remote interface — no cloud, no vendor account, no bridge.

![logo][vestelimg]

The integration is **self-contained**: the protocol lives in
[`custom_components/vestel_tv/api.py`](custom_components/vestel_tv/api.py), so there is
nothing extra to install from PyPI.

> [!WARNING]
> **Verified against exactly one TV** — a Vestel_MB211 (software 3.33.21.0, sold as
> ESSENTIELB). Discovery, state and key codes all work there. Whether older Vestel chassis
> speak the same protocol is untested, and this version removed the legacy channels they
> may rely on — see [Status](#status).

## Features

| Platform       | Description                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------ |
| `media_player` | Power, volume step, mute, source, play/pause/stop, channel up/down, tuning a channel or opening a URL. |
| `button`       | 17 remote keys — D-pad and OK, Back, Exit, Menu, Quick menu, Apps, Info, TV guide, Teletext, Subtitles |

- **Local push** — the TV's state arrives over a WebSocket it keeps open, rather than
  being polled; commands go out immediately as key codes.
- **Automatic discovery** — switched-on TVs are found over SSDP and simply appear in
  Home Assistant waiting to be confirmed. No IP address to type, no ports to hunt for.
- **Zero YAML** — everything is set up through the UI.
- **Rich device information** — model, retail brand, software and hardware version, and
  MAC address, all read from the TV itself.
- **Survives a new DHCP lease** — entries are keyed by the TV's MAC, not its address.

Two limits worth knowing up front. The TV exposes no readable volume *level*, only
relative steps, so `volume_level` stays unknown rather than showing a made-up number. And
power-on only works if the TV is still on the network — see [Troubleshooting](#troubleshooting).

## Supported devices

Vestel manufactures TVs sold under a long list of brand names. Sets reported to speak this
protocol include **Vestel, Procaster, Toshiba, Hitachi, Sharp, JVC, Bush, Alba, Panasonic,
Medion** and **Finlux**. The upstream project was developed against a Procaster LE-50F449.

> [!NOTE]
> Brand alone does not decide it — a manufacturer may ship both Vestel and non-Vestel
> chassis. If the TV's settings menu has a **Virtual Remote** option, it is very likely
> supported.

## Requirements

- Home Assistant **2024.4.0** or newer.
- A Vestel-based TV on the same network/VLAN as Home Assistant, reachable on TCP ports
  **56789** (commands) and **7681** (state), and able to receive SSDP multicast on
  UDP **1900**.
- **Virtual Remote enabled on the TV** — enable it in the TV's settings menu before adding
  the integration. Note that on MB211-era firmware this setting does *not* open the legacy
  TCP port 1986; that port is simply absent regardless.
- A static IP is **no longer required** — config entries are keyed by the TV's MAC address,
  so a changed DHCP lease is still recognised as the same TV. Sets that do not publish a
  MAC in their `dd.xml` fall back to being keyed by address.

> [!NOTE]
> The Vestel icon and logo shipped in
> [`custom_components/vestel_tv/brand/`](custom_components/vestel_tv/brand/) are only
> picked up by Home Assistant **2026.3 or newer**, which added support for custom
> integrations serving their own brand images. On older versions the integration works
> exactly the same, but its card shows Home Assistant's generic "icon not available"
> placeholder, because `vestel_tv` has no entry on the brands CDN.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.][hacs-repo-shield]][hacs-repo]

1. In Home Assistant, open **HACS → ⋮ (top right) → Custom repositories**.
2. Add `https://github.com/tiagoagueda/hass-vestel-tv` with type **Integration**.
3. Search for **Vestel TV**, download it, and restart Home Assistant.

### Manual

1. Open the directory (folder) of your HA configuration (where `configuration.yaml` lives).
2. If there is no `custom_components` directory there, create it.
3. Copy `custom_components/vestel_tv/` from this repository into your `custom_components`
   directory.
4. Restart Home Assistant.

## Configuration

Configuration is done entirely in the UI; there is nothing to add to `configuration.yaml`.

[![Open your Home Assistant instance and start setting up a new integration.][config-flow-shield]][config-flow]

Switched-on Vestel TVs are discovered automatically and appear under
**Settings → Devices & Services** waiting to be confirmed — no address needed.

To add one by hand, or if discovery does not find it:
**Settings → Devices & Services → + Add Integration → Vestel TV**, then enter the TV's IP
address and, optionally, a name. The TV must be switched on, since the flow checks it
answers and is actually a Vestel before creating the entry.

Everything else uses the defaults baked into the stock Vestel protocol — commands on the
DIAL port 56789, state on WebSocket 7681, SSDP/DIAL discovery on 1900. Each TV becomes one
device with a `media_player` entity and 17 remote-key `button` entities.

## Protocol notes

The TV exposes two concurrent interfaces:

| Channel                       | Port         | Purpose                                       |
| ----------------------------- | ------------ | --------------------------------------------- |
| HTTP POST `/apps/SmartCenter` | 56789 (DIAL) | Key codes, text entry, queries, app launching |
| WebSocket `ws://host:7681/`   | 7681         | State broadcasts — channel list, `tv_state`   |

Commands are XML bodies POSTed with an `application_name: tv smart centre` header; the TV
answers `201 Created`. Replies to queries never come back in the POST body — they arrive
on the WebSocket, so the client keeps that socket open.

> [!IMPORTANT]
> The WebSocket handshake **must** carry an `Origin: http://<tv-ip>` header. Without it the
> connection is accepted and then stays silent indefinitely, with no error.

This is not the protocol `pyvesteltv` implements. On MB211-era firmware the older channels
— key codes to `vr/remote`, state over TCP 1986 — are gone entirely: `vr/remote` returns
404 on every path, and 1986 appears nowhere in a sweep of all 65535 ports, with the TV on
and Virtual Remote enabled.

Two consequences worth knowing before you file a bug:

- **Power-on only works if the TV was turned off through this integration.** Turned off
  with the physical remote, the TV drops off WiFi entirely and cannot be reached at all;
  waking it needs Wake-on-LAN, which is not implemented yet.
- **Source selection cycles.** There is no direct-select command, so `select_source` sends
  the *source* key repeatedly and re-reads the state until the requested input comes up.

## Status

**v0.5.0 — verified against one TV.** On a Vestel_MB211 (software 3.33.21.0, ESSENTIELB),
these are confirmed working on real hardware: SSDP discovery, the WebSocket state channel,
the parsed channel list, key codes — volume up/down were observed changing the TV — and
setting the integration up end to end in Home Assistant.

Key codes 1012/1013/1016/1017 and the digits are confirmed on that TV, and 1010 (back) and
1037 (exit) were captured from Vestel's own app. The remaining button codes come from
[node-red-contrib-vestel-tv][nodered] and agree with those, but are **unverified here** —
if a button does nothing on your set, that is the likely reason.

Confirmed *not* available on that firmware, and so unsupported here: reading the current
volume level or mute state. The protocol exposes only relative volume steps, so
`volume_level` reports unknown rather than a made-up number.

Untested and unverified: power on/off, mute, source cycling, text entry and app launching.
They are implemented against the captured protocol and the TV accepts them, but their
effect has not been confirmed. Older Vestel chassis may still use the legacy `vr/remote`
and TCP 1986 channels this version removed — if your set stopped working at 0.3.0, that
is the likely cause and worth an issue.

Reports from any Vestel-based set — working or not — are very welcome on the
[issue tracker][issues]; please include your TV's brand, model, `tv_version` and debug logs.

Not yet implemented: Wake-on-LAN power-on, media title/program attributes, and exposing
the TV's channel list as the source list.

## Troubleshooting

### The TV is added but always shows as *off*

- Confirm **Virtual Remote** is enabled in the TV's settings menu.
- Confirm the TV is actually powered on — a Vestel set that was switched off with the
  physical remote leaves the network and cannot answer.
- Check that Home Assistant and the TV are on the same subnet. SSDP discovery uses
  multicast, which most routers do not forward across VLANs.
- From the HA host, verify both ports answer: `nc -vz <tv-ip> 56789` and
  `nc -vz <tv-ip> 7681`.

### Commands are ignored

Key codes are sent to the DIAL-discovered HTTP endpoint. If discovery has not completed,
commands are silently dropped and logged at debug level — enable debug logging to confirm.

### Enabling debug logs

Open the integration page and use **Enable debug logging**, or add to
`configuration.yaml` and restart:

```yaml
logger:
  default: warning
  logs:
    custom_components.vestel_tv: debug
```

Please include these logs when opening an issue.

## Contributing

Bug reports and pull requests are welcome — please open them on the
[issue tracker][issues] and read the [contribution guidelines](CONTRIBUTING.md) first.
When reporting a problem, include your Home Assistant version, the integration version,
your TV's brand and model, and debug logs.

Notable changes are recorded in the [changelog](CHANGELOG.md).

## Credits

This is a modernized fork of [@T3m3z](https://github.com/T3m3z)'s
[HA-Vestel-Component](https://github.com/T3m3z/HA-Vestel-Component), with the
[pyvesteltv](https://github.com/T3m3z/pyvesteltv) protocol library vendored into the
integration. All of the reverse-engineering credit belongs there.

The wordmark in [`custom_components/vestel_tv/brand/`](custom_components/vestel_tv/brand/)
is Vestel's own, taken from [vestelinternational.com](https://vestelinternational.com/)
and used only to identify the hardware this integration talks to. "Vestel" is a trademark
of Vestel Elektronik Sanayi ve Ticaret A.Ş.; this is an unofficial community project with
no affiliation to or endorsement by Vestel.

## License

MIT — see [LICENSE](LICENSE).

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/tiagoagueda/hass-vestel-tv.svg?style=for-the-badge
[commits]: https://github.com/tiagoagueda/hass-vestel-tv/commits/main
[config-flow]: https://my.home-assistant.io/redirect/config_flow_start/?domain=vestel_tv
[config-flow-shield]: https://my.home-assistant.io/badges/config_flow_start.svg
[forum]: https://community.home-assistant.io/
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs-repo]: https://my.home-assistant.io/redirect/hacs_repository/?owner=tiagoagueda&repository=hass-vestel-tv&category=integration
[hacs-repo-shield]: https://my.home-assistant.io/badges/hacs_repository.svg
[issues]: https://github.com/tiagoagueda/hass-vestel-tv/issues
[nodered]: https://github.com/hyttysmyrkky/node-red-contrib-vestel-tv
[license-shield]: https://img.shields.io/github/license/tiagoagueda/hass-vestel-tv.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40tiagoagueda-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/tiagoagueda/hass-vestel-tv.svg?style=for-the-badge
[releases]: https://github.com/tiagoagueda/hass-vestel-tv/releases
[user_profile]: https://github.com/tiagoagueda
[vestelimg]: custom_components/vestel_tv/brand/logo.png
