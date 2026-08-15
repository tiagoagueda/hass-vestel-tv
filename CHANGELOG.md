# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version that matters to users is the `version` field in
[`custom_components/vestel_tv/manifest.json`](custom_components/vestel_tv/manifest.json) —
that is what HACS reads to offer an update.

## [Unreleased]

## [0.4.0] - 2026-08-15

### Added

- **Automatic discovery.** Vestel TVs are now offered in Home Assistant without
  typing an address, using the same SSDP search target Vestel's own app uses
  (`urn:dial-multiscreen-org:service:dial:1`).
- **The config flow now checks the TV before creating an entry.** It fetches the
  TV's `dd.xml` and fails the form with *cannot connect* if nothing answers, or
  *not a Vestel TV* if something answers but is not one. Previously any string
  was accepted, so a typo produced an entry that silently never worked.

### Changed

- **Config entries are keyed by the TV's MAC address instead of its IP**
  (config entry version 2, migrated automatically on upgrade). A TV that picks
  up a new DHCP lease is now recognised as the same device rather than
  reappearing as a new one, so a static lease is no longer required. Sets that
  do not publish a MAC in `dd.xml` still fall back to the address, and a TV that
  is unreachable at migration keeps its old key rather than failing to load.
- Discovered and manually added TVs are named from the TV's own `friendlyName`,
  with the MAC suffix Vestel appends to it stripped — `ESSENTIELB`, not
  `ESSENTIELB_cc:d3:c1:49:77:52`.

### Notes

Every DIAL device on a network answers the search target above — Chromecasts,
streaming sticks, other TVs — so discovery deliberately verifies each responder
before offering it, by looking for the fields Vestel adds to `dd.xml`
(`verificationKey`, `tv_version`). This mirrors what the official app does; its
own log string for the rejection case is *"non-smartcenter UPnP device msearch
is masked"*.

## [0.3.0] - 2026-08-15

First version verified against real hardware (a Vestel_MB211, software
3.33.21.0, sold as ESSENTIELB). Everything before this was unverified.

### Changed

- **`api.py` now speaks Vestel's own "TV Smart Centre" protocol.** Commands are
  POSTed as XML to the DIAL app endpoint `{app_url}SmartCenter` with an
  `application_name: tv smart centre` header, and the TV answers `201 Created`.
  Confirmed moving the real TV's volume.
- **State now arrives over the WebSocket on port 7681**, replacing the TCP 1986
  polling that never worked. The handshake must carry an `Origin` header;
  without it the socket connects and then stays silent forever. The client holds
  the socket open and reconnects, so `iot_class` is now `local_push`.
- `media_player` gained a `source_list` (it advertised `SELECT_SOURCE` without
  one), and `volume_level` reports unknown instead of a fabricated `0`.

### Added

- `async_send_text()` — types a string on the TV, one POST per character, as the
  official app does.
- `async_send_command()` and `async_load_url()` for the TV's query commands
  (`tvstate`, `activechannellist`, …) and portal-app launching.
- The TV's channel list is parsed from `<active_list>` broadcasts into
  `VestelTV.channels`.

### Removed

- The TCP 1986 client (`_read_tcp`/`_query`) and `DEFAULT_PORT_TCP`. That port
  does not exist on MB211-era firmware — a sweep of all 65535 ports found it
  nowhere, with the TV powered on and "Virtual Remote" enabled — and neither
  does `vr/remote`, which returns 404 on every path.

### Fixed

- SSDP discovery bound its socket to `0.0.0.0` without setting
  `IP_MULTICAST_IF`, so the `M-SEARCH` left via whichever interface won the
  routing table. On a multi-homed host (Docker bridges, VPN adapters, hypervisor
  switches) the TV was never found, and the failure was silent — `discovered`
  simply stayed `False`. Discovery now pins multicast to the interface that
  routes to the configured host.

## [0.2.0] - 2026-08-15

### Added

- Config-flow UI strings (`strings.json`) with English (`en`), French (`fr`) and
  Portuguese (`pt`) translations. The flow previously fell back to raw key names.
- `CHANGELOG.md`, `CONTRIBUTING.md` and `CLAUDE.md`.
- Integration artwork in `custom_components/vestel_tv/brand/` (`icon`/`logo`, 1× and 2×),
  rendered from the official Vestel wordmark on
  [vestelinternational.com](https://vestelinternational.com/) to the
  [brands spec](https://github.com/home-assistant/brands#image-specification), plus a
  trademark notice in the README covering their use. Home Assistant **2026.3+** serves
  these in place of the "icon not available" placeholder it showed before, since
  `vestel_tv` has no entry on the brands CDN.

### Changed

- `documentation` and `issue_tracker` in `manifest.json` now point at the public GitHub
  mirror, which is what HACS installs from. `source.tiagoagueda.com` remains the only git
  remote and the source of truth.
- Rewritten `README.md` with badges, requirements, supported devices, protocol notes,
  troubleshooting and debug-logging instructions.
- `.gitattributes` now marks `*.png` as binary; `.gitignore` reorganized by category.
- `hacs.json` trimmed to `name` and `homeassistant`; the speculative `country` list is
  gone, since Vestel-based sets are sold well beyond it.

### Fixed

- Declared minimum Home Assistant version raised from `2024.1.0` to `2024.4.0` in both
  `hacs.json` and `manifest.json`. The config flow imports `ConfigFlowResult`, which does
  not exist before 2024.4, so setup would have failed on the versions previously claimed
  as supported.
- Removed the `websockets>=11.0` requirement from `manifest.json`. Nothing in the
  integration imports it — the WebSocket channel is documented but not yet implemented —
  so Home Assistant was installing a package it never used.

## [0.1.0] - 2026-08-15

### Added

- Initial scaffold: a UI config flow and a `media_player` platform with power, volume
  step, mute and source cycling, built on an async aiohttp/asyncio port of `pyvesteltv`
  vendored into `api.py`.

---

Releases up to and including 0.1.0 predate this repository's own history — the integration
is forked from [T3m3z/HA-Vestel-Component](https://github.com/T3m3z/HA-Vestel-Component)
and [T3m3z/pyvesteltv](https://github.com/T3m3z/pyvesteltv), which carry the per-commit
history of the original component and protocol library.

[unreleased]: https://github.com/tiagoagueda/hass-vestel-tv/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/tiagoagueda/hass-vestel-tv/releases/tag/v0.4.0
[0.3.0]: https://github.com/tiagoagueda/hass-vestel-tv/releases/tag/v0.3.0
[0.2.0]: https://github.com/tiagoagueda/hass-vestel-tv/releases/tag/v0.2.0
[0.1.0]: https://github.com/tiagoagueda/hass-vestel-tv/releases/tag/v0.1.0
