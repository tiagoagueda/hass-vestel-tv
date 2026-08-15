# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version that matters to users is the `version` field in
[`custom_components/vestel_tv/manifest.json`](custom_components/vestel_tv/manifest.json) —
that is what HACS reads to offer an update.

## [Unreleased]

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

[unreleased]: https://github.com/tiagoagueda/hass-vestel-tv/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/tiagoagueda/hass-vestel-tv/releases/tag/v0.2.0
[0.1.0]: https://github.com/tiagoagueda/hass-vestel-tv/releases/tag/v0.1.0
