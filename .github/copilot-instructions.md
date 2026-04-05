# Copilot Instructions

## Project Overview

Home Assistant custom integration (`smart_venetian_blinds`) that calculates optimal venetian blind slat angles from sun position, facade orientation, and slat geometry — all computed locally with no external API.

**Domain:** `smart_venetian_blinds` | **IoT Class:** `calculated` | **Python:** ≥3.13.2

## Commands

```bash
script/check          # Full validation: type-check + lint + spell (run before committing)
script/type-check     # Pyright (basic mode)
script/lint           # Ruff auto-format and fix
script/lint-check     # Ruff check without fixing
script/test           # Run all tests
script/test --cov-html  # With HTML coverage report
script/hassfest       # Validate against Home Assistant standards
./script/develop      # Start HA on port 8123 with integration loaded
```

**Run a single test:**
```bash
pytest tests/unit/sun/test_math.py::TestNormalizeAngle180::test_zero_returns_zero -v
pytest tests/unit/sun/test_math.py -v          # Entire file
pytest -k "test_zero_returns_zero" -v          # By name pattern
```

**Restart HA after** modifying Python files, `manifest.json`, `services.yaml`, translations, or config flow changes.

## Architecture

### Data Flow

```
Sun Entity State Change
        │
        ▼
SunStateListener          ← debounced; in sun/listener.py
        │
        ▼
Coordinator               ← calculates slat angles per window group; in coordinator/base.py
        │
   ┌────┴────────────────┐
   ▼                     ▼
Sensor Entities    CoverController   ← only if auto_control is enabled; in cover_control/controller.py
```

### Two-Level Configuration Model

- **Config Entry = Window Group** — shared facade azimuth, slat geometry, throttling settings
- **Subentry = Individual Cover** — target cover entity, drive position, tilt inversion, sleep-mode thresholds

This means `entry.data` holds group config and subentries (accessed via `entry.subentries`) hold per-cover config.

### Key Classes

| Class | Location | Role |
|---|---|---|
| `SmartVenetianBlindsDataUpdateCoordinator` | `coordinator/base.py` | Central coordinator; exported from `coordinator/__init__.py` |
| `GroupState` | `coordinator/state.py` | Throttling state, auto_control flag, no-sun tracking per group |
| `SunStateListener` | `sun/listener.py` | Debounced listener for `sun.sun` or solar sensor changes |
| `SunDataProvider` | `sun/provider.py` | Reads azimuth/elevation from HA sun entity or solar sensors |
| `CoverController` | `cover_control/controller.py` | Drive-then-tilt logic; respects sleep mode and tilt inversion |
| `SmartVenetianBlindsEntity` | `entity/base.py` | Base for all entities in the integration |

### Slat Angle Calculation

All math is in `sun/math.py`. Core inputs: sun azimuth, sun elevation, facade azimuth, slat width, slat spacing. The facade's sun exposure window (±90° from facade normal) determines if the sun hits the window at all.

## Key Conventions

**Entity access pattern — never call HA API directly from entities:**
```python
# Always go through coordinator
self.coordinator.data.calculated_angle
```

**Service registration goes in `async_setup()`, not `async_setup_entry()`:**
```python
async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    await async_setup_services(hass)
    return True
```

**Unique IDs follow `{entry_id}_{description.key}` pattern** — see `entity/base.py`.

**All integration classes are prefixed `SmartVenetianBlinds`** (e.g., `SmartVenetianBlindsEntity`, `SmartVenetianBlindsConfigFlowHandler`).

**Adding a new platform:**
1. Create `custom_components/smart_venetian_blinds/<platform>/` with `__init__.py` (implements `async_setup_entry`) and entity file
2. Entity classes inherit from both the HA platform base (e.g., `SensorEntity`) and `SmartVenetianBlindsEntity`
3. Add platform to `PLATFORMS` list in `const.py`

**Adding a new service action:**
1. Implement handler in `service_actions/<name>.py`
2. Define in `services.yaml`
3. Register in `__init__.py:async_setup()` — not `async_setup_entry()`

**All config/option keys are in `const.py`** — use constants, never bare strings, for config access.

**Import aliases enforced by Ruff:**
```python
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
import homeassistant.util.dt as dt_util
```

**Docstrings use Google style** (`pyproject.toml`: `convention = "google"`).

**Line length:** 120 characters. **Type hints:** required everywhere. **Async:** required for all I/O.

## Test Structure

Tests mirror source under `tests/unit/`. Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration`. Shared fixtures in `tests/conftest.py` (sun positions, calculation results, cover configs).

Warnings are treated as errors in pytest (`filterwarnings = ["error"]`); don't suppress unless necessary.

## Translations

UI strings live in `translations/en.json` (and `de.json`). Config flow schema keys must match translation keys. Run `script/hassfest` to validate translation structure.
