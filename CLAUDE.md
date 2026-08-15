# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **self-contained Home Assistant custom integration** (HACS, category `integration`) for Vestel-built smart TVs, controlled over the TV's "Virtual Remote" LAN interfaces. Everything shippable lives under [custom_components/vestel_tv/](custom_components/vestel_tv/); the rest of the repo is documentation.

This is a **distribution-only repo**: there is no build system, no dependency manager, no test suite, no linters, no CI. Nothing here is installed or compiled — Home Assistant imports the files as they are. Do not add `poetry`/`uv`/`pytest` commands to docs or assume they exist; if you need that tooling, add it deliberately and update this file.

**The integration has never been run against a live TV.** Treat every behavioural claim in the code as unverified. Do not write documentation that asserts a feature works; say what it is intended to do and keep the caveats in [README.md](README.md) → Status honest.

Git origin is a self-hosted Forgejo instance (`source.tiagoagueda.com`) and is the **only** remote — do not add a `github` remote. `github.com/tiagoagueda/hass-vestel-tv` is a mirror pushed by Forgejo, and it is the URL HACS installs from (HACS custom repositories accept GitHub only), so all user-facing links in docs and `manifest.json` must point at GitHub while all pushes go to Forgejo.

## Versioning & releases

**Only one version number exists**: `version` in [manifest.json](custom_components/vestel_tv/manifest.json). Bump it by hand when you want HACS to offer users an update, and add a matching entry to [CHANGELOG.md](CHANGELOG.md). HACS picks the new version up from a GitHub release (or the default branch).

The minimum Home Assistant version is declared in **two** places that must agree: `homeassistant` in [manifest.json](custom_components/vestel_tv/manifest.json) and in [hacs.json](hacs.json). It is currently `2024.4.0`, set by `ConfigFlowResult` in [config_flow.py](custom_components/vestel_tv/config_flow.py) — raise it if you adopt a newer HA API.

There are **no third-party runtime requirements**: `requirements` in the manifest is empty and should stay that way. `aiohttp` and `voluptuous` are provided by Home Assistant itself, and everything else is stdlib. Do not re-add `websockets` — the WebSocket channel is documented but not implemented, and declaring it makes HA install a package nothing imports.

## Protocol client (`api.py`)

[api.py](custom_components/vestel_tv/api.py) is a vendored, modernized port of [T3m3z/pyvesteltv](https://github.com/T3m3z/pyvesteltv). Keep Home Assistant imports out of it — it must stay a plain async client. The TV speaks three channels at once:

- **SSDP/DIAL discovery** (UDP 1900) — `_DialDiscovery` is an `asyncio.DatagramProtocol` that re-broadcasts an `M-SEARCH` every `DISCOVERY_INTERVAL` (5 s), filters replies to the configured host, and fetches the `LOCATION` URL to read its `Application-URL` header. `discovered` is a freshness check: true only if a reply was resolved within `DISCOVERY_TIMEOUT` (16 s). The resolved `app_url` is the base for key-code POSTs; with no discovery there is no way to send anything, and `async_send_key` silently no-ops at debug level.
- **HTTP key codes** — `POST {app_url}vr/remote` with an XML body `<remote><key code="…"/></remote>`. Codes live in [const.py](custom_components/vestel_tv/const.py) (`KEY_*`, `KEYS_DIGIT`).
- **TCP state** (port 1986) — `_read_tcp` opens a connection per poll and issues line commands (`GETMUTE`, `GETSOURCE`, `GETPROGRAM`, `GETHEADPHONEVOLUME`), parsing `"… is VALUE"` replies via `_query`. A failed read is interpreted as *TV off*, because a Vestel set that is off drops off the network entirely.
- **WebSocket** (port 7681) — the TV broadcasts state here. `DEFAULT_PORT_WS` is reserved but nothing consumes it yet; wiring it up would turn this integration from `local_polling` into `local_push` (remember to change `iot_class`).

Two protocol quirks drive the entity behaviour and must survive refactors:

- **Power-on is one-way.** `KEY_POWER` toggles, and the TV only listens while it is on the network. Turned off with the physical remote it leaves WiFi and is unreachable, so `async_turn_on` can only work if this integration turned it off. Wake-on-LAN is the fix and is not implemented.
- **Source selection has no direct-select.** `async_select_source_step` sends the *source* key once; [media_player.py](custom_components/vestel_tv/media_player.py) loops it up to 10 times, re-polling after each step, until `source` matches.

## Integration architecture (`custom_components/vestel_tv/`)

- [`__init__.py`](custom_components/vestel_tv/__init__.py) — `async_setup_entry` builds a `VestelTV` on HA's shared aiohttp session, starts SSDP discovery, and stores it in `hass.data[DOMAIN][entry.entry_id]`. This is the older storage pattern; if you migrate to `entry.runtime_data`, update both platform lookup and the minimum HA version.
- [config_flow.py](custom_components/vestel_tv/config_flow.py) — a single `user` step asking for host and optional name. The unique ID is the **host**, so a TV that changes IP appears as a new device; the docs tell users to reserve a static lease.
- [media_player.py](custom_components/vestel_tv/media_player.py) — the only platform (`Platform.MEDIA_PLAYER`). A plain polling `MediaPlayerEntity` (no coordinator) with `SCAN_INTERVAL` from `DEFAULT_SCAN_INTERVAL` (30 s). `_attr_has_entity_name = True` with `_attr_name = None`, so the entity takes the device name.
- Config-flow UI strings: [strings.json](custom_components/vestel_tv/strings.json) is the source, but custom integrations are **not** processed by Core's translation build step, so a literal-English [translations/en.json](custom_components/vestel_tv/translations/en.json) (with `[%key:…%]` references resolved) must be shipped and kept in sync, alongside [fr.json](custom_components/vestel_tv/translations/fr.json) and [pt.json](custom_components/vestel_tv/translations/pt.json).

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/). Nothing enforces or automates this here — it is stylistic.
- Code style is `ruff`-formatted (88 cols, double quotes), even though no formatter runs in this repo.
- [images/](images/) holds the README brand assets, rendered from the official Vestel wordmark (an inline SVG in the header of [vestelinternational.com](https://vestelinternational.com/), brand red `#DF2228`) at the same sizes the reference repo uses: `icon` 256/512 px square, `logo` 256/512 px tall. Do **not** pull replacements from `brands.home-assistant.io` — there is no Vestel entry there, and the `_/vestel/` path serves an "icon not available" placeholder. The README carries a trademark notice for these; keep it if you touch the Credits section.
- When extending: keep the wire protocol in `api.py`, keep HA imports out of it, bump `manifest.json` `version` and update `CHANGELOG.md` to release.
