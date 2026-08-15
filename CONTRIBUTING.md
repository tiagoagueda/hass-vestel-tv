# Contributing

Contributions are welcome — bug reports, protocol findings, fixes and new features.

Because this integration has **not yet been verified against a live TV**, the single most
useful contribution right now is a report from a real device: does it work, on which brand
and model, and what broke.

## Reporting bugs

Open an issue on the [issue tracker](https://github.com/tiagoagueda/hass-vestel-tv/issues).
A good report includes:

- Home Assistant version and integration version (`manifest.json` → `version`).
- The TV's brand and exact model number, and whether its settings menu has a
  **Virtual Remote** option.
- Whether the TV was last switched off via Home Assistant or via the physical remote —
  this changes whether it is reachable at all.
- What you expected, what actually happened, and steps to reproduce.
- Debug logs — see [Enabling debug logs](README.md#enabling-debug-logs) in the README.

Protocol findings are just as welcome as bugs: new key codes, TCP query commands, or a
capture of what the TV broadcasts over the WebSocket on port 7681.

## Pull requests

1. Fork the repo and branch from `main`.
2. Keep the change focused, and update the documentation it affects.
3. Follow the existing style: `ruff`-formatted Python (88 columns, double quotes),
   type hints on public functions, `from __future__ import annotations` at the top.
4. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit
   messages (`fix:`, `feat:`, `docs:`, `chore:` …).
5. Add an entry under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md).
6. Open the pull request.

## Repository layout

This repo ships the integration and nothing else — no build system, no test suite,
no linters, no CI. Home Assistant loads the files as they are.

```text
custom_components/vestel_tv/               # the integration (HA-facing code)
custom_components/vestel_tv/api.py         # vendored TV protocol client
custom_components/vestel_tv/translations/  # config-flow translations
hacs.json                                  # HACS metadata
```

Keep the TV wire protocol inside [`api.py`](custom_components/vestel_tv/api.py) and keep
Home Assistant imports out of it, so it stays testable and reusable on its own. The
platform modules should only translate between that client and Home Assistant entities.

## Testing a change

There is no automated test suite. To verify a change by hand:

1. Copy `custom_components/vestel_tv/` into your Home Assistant `config/custom_components/`
   directory (or symlink it) and restart Home Assistant.
2. Add the integration and exercise power on/off, volume up/down, mute and source
   selection — including changes made with the physical remote, to confirm the polled
   state follows.
3. Attach the debug logs for the scenario you fixed to the pull request.

## Releasing (maintainers)

1. Bump `version` in [`custom_components/vestel_tv/manifest.json`](custom_components/vestel_tv/manifest.json).
2. Move the `## [Unreleased]` entries into a new dated version section in `CHANGELOG.md`.
3. Tag and publish a GitHub release on the mirror — HACS offers the update from there.

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](LICENSE).
