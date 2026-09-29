# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for sun-position-driven venetian blind control. It calculates optimal slat angles based on sun position, facade orientation, and slat geometry to block direct sunlight while maximizing daylight.

**Domain:** `smart_venetian_blinds`
**Integration Type:** Hub (supports multiple window groups, each with multiple covers)
**IoT Class:** Calculated (no external API - all computation local)

## Development Commands

```bash
# Full validation (run before committing)
script/check              # Runs type-check + lint + spell

# Individual checks
script/type-check         # Pyright type checking
script/lint               # Ruff auto-format and fix
script/lint-check         # Ruff check without fixing
script/spell              # Spellcheck

# Local Home Assistant testing
./script/develop          # Start HA on port 8123 with integration loaded
                          # Stops this worktree's own instance first - no manual pkill needed

# Emergency cleanup only, if a stale process survived script/develop.
# Keep the path filter: a bare `pkill -f "hass --config"` kills every Home Assistant
# on the machine, including instances belonging to other worktrees.
pkill -f "hass --config.*${PWD}/config" || true

# Validate against HA standards
script/hassfest           # Official Home Assistant validation

# Tests
script/test               # Run all tests
script/test --cov-html    # With coverage report
```

**When to restart HA:** After modifying Python files, `manifest.json`, `services.yaml`, translations, or config flow changes.

**One Home Assistant per machine:** port 8123 and the debugpy port 5678 are machine-wide, so two
worktrees cannot run Home Assistant at the same time. `script/develop` only stops the instance
belonging to its own worktree; if another worktree is already running one, it refuses to start and
names the process holding the port. Stop that instance first.

**Logs:** Live in terminal running `./script/develop`, or in `config/home-assistant.log`

## Release Process

Releases are automated end to end. Do not bump the version, regenerate diagrams,
or create tags by hand.

**1. Pick the version number.** A `feat:` commit on main since the last tag means a
minor bump (0.7.7 → 0.8.0); only fixes and refactors means a patch bump. Nothing
verifies this — `release-prepare` validates the `X.Y.Z` format and nothing else, so
the choice is entirely yours at the prompt.

**2. Actions → "Prepare release" → Run workflow**, and enter the version.
`release-prepare.yml` bumps `manifest.json`, regenerates the behavior diagrams, and
opens a `chore/release-<version>` PR with both changes. Normal CI runs on it.

**3. Squash or rebase merge that PR — never "Create a merge commit."**
`release-tag.yml` reads `git log -1 --pretty=%s` on main and requires it to match
`chore: release X.Y.Z`. A merge commit reads `Merge pull request #N from …`, which
fails that check, so the tag and the GitHub Release are skipped **silently** — the
workflow reports success. Merge commits are still enabled on this repo, so this is
one wrong dropdown away.

**4. Nothing.** `release-tag.yml` fires on the `manifest.json` change, creates the
tag (no `v` prefix — ever) and publishes a GitHub Release with generated notes.

**Never use `script/release`.** It predates the automation and commits
`chore: bump version to X.Y.Z`, which does not match the pattern in step 3. You get
a tag but no GitHub Release.

**Diagrams are CI's job now.** `release-prepare.yml` regenerates them as part of the
release PR, so there is no pre-tag step to remember. `diagrams-preview.yml` renders
them on every PR touching the integration and posts them as a preview comment, so a
broken import in `script/visualize` fails a check instead of surfacing at release
time. Run `script/visualize` locally only to spot-check your own changes; do not
commit its output. `update-diagrams.yml` predates all of this, is `workflow_dispatch`
only, and is now redundant with the release flow.

## Architecture

### Data Flow

```bash
Sun Entity Changes → SunStateListener → Coordinator → CoverController → Cover Entities
                                              ↓
                                    Sensor Entities (calculated angles)
```

### Package Structure

```bash
custom_components/smart_venetian_blinds/
├── __init__.py              # Entry setup, sun listener, event-driven cover control
├── const.py                 # All constants and configuration keys
├── data.py                  # Runtime data types (SmartVenetianBlindsData)
├── diagnostics.py           # Diagnostic data for troubleshooting
├── repairs.py               # Repair flows for fixing issues
├── coordinator/             # DataUpdateCoordinator for slat calculations
│   ├── base.py              # Main coordinator class
│   └── state.py             # GroupState (throttling, auto_control, no-sun tracking)
├── sun/                     # Sun position handling
│   ├── provider.py          # SunDataProvider (reads sun.sun or sensors)
│   ├── listener.py          # SunStateListener (debounced state tracking)
│   └── math.py              # Slat angle calculations, SunPosition, SlatCalculationResult
├── cover_control/           # Cover tilt application
│   └── controller.py        # CoverController (drive-then-tilt logic)
├── config_flow_handler/     # Config flow implementation
│   ├── config_flow.py       # Main ConfigFlow class
│   ├── options_flow.py      # Options flow
│   ├── subentry_flow.py     # Cover subentry flow
│   ├── schemas/             # Form schemas (group, cover_subentry, options)
│   └── validators/          # Input validation (__init__.py only)
├── entity/                  # Base entity class
├── entity_utils/            # Device info helpers (create_window_group_device_info)
├── sensor/                  # Sensor platform (slat angle, sun position)
├── switch/                  # Switch platform (auto_control toggle)
├── service_actions/         # Service implementations (apply_now)
└── utils/                   # String helpers (slugify_name, truncate_string)
```

### Key Concepts

**Window Groups (Config Entries):** Each config entry is a window group with:

- Shared facade azimuth (compass direction the window faces)
- Slat geometry (width, spacing)
- Update throttling settings

**Covers (Subentries):** Each subentry is an individual cover with:

- Target cover entity ID
- Drive position (where to position before tilting)
- Tilt inversion settings
- Manual close detection threshold ("sleep mode")
- No-sun behavior configuration

**Event-Driven Updates:** The integration listens for `sun.sun` or `sensor.sun_solar_*` state changes. When sun moves, it:

1. Updates coordinator data (sensor values)
2. Checks `auto_control_enabled` flag
3. If enabled, applies calculated tilt to all covers

**Auto Control Switch:** Each window group has a `switch.<group>_auto_control` entity. When OFF, sun changes still update sensors but don't move covers.

### Important Patterns

- **Entities never call API directly** - always go through coordinator
- **Services registered in `async_setup()`**, not `async_setup_entry()`
- **Unique IDs:** `{entry_id}_{description.key}` for entities
- **Class prefix:** `SmartVenetianBlinds` for all integration classes
- **Python style:** 4 spaces, 120 char lines, full type hints, async for I/O

## Code Quality

Validation tools are pre-configured:

- **Ruff** for linting/formatting
- **Pyright** for type checking (basic mode)
- **cSpell** for spell checking

Run `script/check` before committing - it should pass with zero errors.

## Additional Documentation

- `docs/development/ARCHITECTURE.md` - Technical architecture docs
- `docs/development/DECISIONS.md` - Architecture Decision Records
