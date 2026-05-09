# Vestel TV — Home Assistant integration

A modernized fork of [T3m3z/HA-Vestel-Component](https://github.com/T3m3z/HA-Vestel-Component) with the [pyvesteltv](https://github.com/T3m3z/pyvesteltv) protocol logic vendored in.

Adds:
- UI config flow (no YAML required)
- Async aiohttp + asyncio (no deprecated `loop=` kwargs)
- HACS-installable as a custom repository
- Targets modern Home Assistant (2024.1+)

## Compatibility

Vestel-built TVs sold under various brand names: Vestel, Procaster, Toshiba, Hitachi, Sharp, JVC, Bush, Alba, Panasonic, Medion, Finlux. Originally tested on Procaster LE-50F449.

The TV's "Virtual Remote" feature must be enabled in the TV settings menu before this integration can talk to it.

## Status

**v0.1.0 — minimal scaffold, untested against a live TV.** Power, volume, mute, and source-cycle work in theory but have not been verified yet.

Known limitations of the underlying protocol:
- Power-on only works if the TV was last turned off via this integration. If the TV was turned off via the physical remote, it disconnects from WiFi and cannot be woken without Wake-on-LAN (not yet implemented).
- Source selection cycles (no direct-select API), so `select_source` walks through inputs until it lands on the requested one.

## Installation

### Via HACS (custom repository)

1. HACS → Integrations → ⋮ → Custom repositories
2. Add `https://source.tiagoagueda.com/tiagoagueda/hass-vestel-tv` as type **Integration**
3. Install "Vestel TV"
4. Restart Home Assistant
5. Settings → Devices & services → Add integration → "Vestel TV"

### Manual

Copy `custom_components/vestel_tv/` into your Home Assistant config directory's `custom_components/` folder, then restart and add the integration via the UI.

## Configuration

Only the TV's IP address is required. Everything else uses defaults that match Vestel's stock protocol (TCP 1986, WS 7681, SSDP/DIAL discovery on 1900).

## Protocol notes

Three concurrent interfaces, all discovered or hard-coded:

| Channel | Port | Purpose |
| --- | --- | --- |
| HTTP POST `/vr/remote` | dynamic (DIAL) | Send key codes (XML body) |
| TCP socket | 1986 | State queries (`GETMUTE`, `GETSOURCE`, `GETHEADPHONEVOLUME`, ...) |
| WebSocket `ws://host:7681/` | 7681 | State broadcasts (not yet consumed by this integration) |

## Credits

- Original library and component: [T3m3z](https://github.com/T3m3z) — MIT-licensed.
- Modernization and HA 2024+ porting: this fork.

## License

MIT
