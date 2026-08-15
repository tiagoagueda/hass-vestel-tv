# Vestel TV

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![Community Forum][forum-shield]][forum]

Home Assistant custom integration for Vestel-built smart TVs, controlled locally over
the TV's own "Virtual Remote" interface — no cloud, no vendor account, no bridge.

![logo][vestelimg]

The integration is **self-contained**: the `pyvesteltv` protocol logic is vendored into
[`custom_components/vestel_tv/api.py`](custom_components/vestel_tv/api.py), so there is
nothing extra to install from PyPI.

> [!WARNING]
> **v0.2.0 is an untested scaffold.** The code is complete but has not yet been verified
> against a live TV. Expect rough edges and please report what you find — see
> [Status](#status).

## Features

| Platform       | Description                                                           |
| -------------- | --------------------------------------------------------------------- |
| `media_player` | Power on/off, volume step, mute toggle and source selection for a TV. |

- **Local polling** — the TV's state (power, mute, volume, source, program) is read every
  30 s over a plain TCP socket; commands go out immediately as key codes.
- **Zero YAML** — the TV is added through a UI config flow; only its IP address is needed.
- **Automatic endpoint discovery** — the HTTP remote endpoint is resolved via SSDP/DIAL,
  so no port hunting is required.

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
  **1986** and **7681**, and able to receive SSDP multicast on UDP **1900**.
- **Virtual Remote enabled on the TV** — without it the TV ignores every command. Enable
  it in the TV's settings menu before adding the integration.
- A static IP (or DHCP reservation) for the TV, since the config entry is keyed by address.

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

**Settings → Devices & Services → + Add Integration → Vestel TV**, then enter the TV's IP
address and, optionally, a name.

Everything else uses the defaults baked into the stock Vestel protocol — TCP 1986,
WebSocket 7681, SSDP/DIAL discovery on 1900. Each TV becomes one device with a single
`media_player` entity.

## Protocol notes

The TV exposes three concurrent interfaces:

| Channel                | Port           | Purpose                                                   |
| ---------------------- | -------------- | --------------------------------------------------------- |
| HTTP POST `/vr/remote` | dynamic (DIAL) | Send key codes as an XML body                             |
| TCP socket             | 1986           | State queries (`GETMUTE`, `GETSOURCE`, `GETPROGRAM`, …)   |
| WebSocket `ws://host/` | 7681           | State broadcasts — *not yet consumed by this integration* |

Two consequences worth knowing before you file a bug:

- **Power-on only works if the TV was turned off through this integration.** Turned off
  with the physical remote, the TV drops off WiFi entirely and cannot be reached at all;
  waking it needs Wake-on-LAN, which is not implemented yet.
- **Source selection cycles.** There is no direct-select command, so `select_source` sends
  the *source* key repeatedly and re-reads the state until the requested input comes up.

## Status

**v0.2.0 — feature-complete scaffold, unverified against real hardware.** Power, volume,
mute and source cycling are implemented but have not been confirmed on a live TV. Reports
from any Vestel-based set — working or not — are very welcome on the
[issue tracker][issues]; please include your TV's brand and model and debug logs.

Not yet implemented: Wake-on-LAN power-on, WebSocket push updates, media title/program
attributes, and a configurable source list.

## Troubleshooting

### The TV is added but always shows as *off*

- Confirm **Virtual Remote** is enabled in the TV's settings menu.
- Confirm the TV is actually powered on — a Vestel set that was switched off with the
  physical remote leaves the network and cannot answer.
- Check that Home Assistant and the TV are on the same subnet. SSDP discovery uses
  multicast, which most routers do not forward across VLANs.
- From the HA host, verify the state port answers: `nc -vz <tv-ip> 1986`.

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

The wordmark in [`images/`](images/) is Vestel's own, taken from
[vestelinternational.com](https://vestelinternational.com/) and used only to identify the
hardware this integration talks to. "Vestel" is a trademark of Vestel Elektronik Sanayi ve
Ticaret A.Ş.; this is an unofficial community project with no affiliation to or
endorsement by Vestel.

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
[license-shield]: https://img.shields.io/github/license/tiagoagueda/hass-vestel-tv.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40tiagoagueda-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/tiagoagueda/hass-vestel-tv.svg?style=for-the-badge
[releases]: https://github.com/tiagoagueda/hass-vestel-tv/releases
[user_profile]: https://github.com/tiagoagueda
[vestelimg]: images/logo.png
