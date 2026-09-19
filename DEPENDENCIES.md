# Dependencies Overview

This custom integration uses multiple requirements files to separate different types of dependencies:

## 📁 Files

### `requirements.txt` - Runtime Dependencies

**Purpose:** Python packages needed by the integration at runtime
**Installed by:** Home Assistant when loading the integration
**Also defined in:** `custom_components/smart_venetian_blinds/manifest.json`

**Note:** This file is typically empty if this integration has no additional runtime dependencies beyond Home Assistant core.

**Example:**

```txt
aiohttp>=3.8.0
async-timeout>=4.0.0
```

### `requirements_dev.txt` - Development Tools

**Purpose:** Additional development tools beyond what Home Assistant core provides
**Installed by:** `script/setup/bootstrap`
**Used by:** Developers, IDEs

**Includes:**

- `pyright` - Type checker (we prefer pyright over HA's mypy for better IDE integration)
- `ruff` - Linting and formatting
- `codespell` - Spell checking
- `pre-commit` - Git hook framework (`script/setup/bootstrap` runs `pre-commit install`)
- `colorlog` - Colored logging for development scripts
- Performance tools (`zlib_ng`, `isal`) - Optional optimization packages

**Note:** These tools used to come from Home Assistant core's `requirements_test_pre_commit.txt`. That file is not part of the `homeassistant` wheel, so this project pins them itself.

### `requirements_test.txt` - Testing Framework

**Purpose:** Additional testing tools beyond what Home Assistant core provides
**Installed by:** `script/setup/bootstrap`
**Used by:** Test runners, CI/CD

**Includes:**

- `pytest-homeassistant-custom-component` - Additional fixtures and utilities for custom component testing

**Note:** Core testing tools (pytest, pytest-asyncio, pytest-aiohttp, pytest-cov, pytest-timeout, pytest-xdist, coverage, freezegun, requests-mock, respx) are already provided by Home Assistant core's `requirements_test.txt`, which is installed automatically via `script/setup/bootstrap`.

## 🔄 Relationship with manifest.json

### manifest.json `requirements` field

```json
{
  "requirements": ["aiohttp>=3.8.0"]
}
```

- ✅ Runtime dependencies for end users
- ✅ Automatically installed by Home Assistant
- ✅ Should match `requirements.txt` content
- ℹ️ **Optional:** If this integration doesn't need additional packages beyond Home Assistant core, you can omit this field

### When to add dependencies

| Add to | When |
|--------|------|
| `manifest.json` + `requirements.txt` | Runtime dependency (end users need it) |
| `requirements_dev.txt` | Development tool (linting, formatting, type checking) |
| `requirements_test.txt` | Testing tool (pytest plugins, test utilities) |

## 📝 Maintenance

When you add a runtime dependency:

1. ✅ Add to `manifest.json` `requirements` field
2. ✅ Add to `requirements.txt` (same version constraint)
3. ❌ Don't add to `requirements_dev.txt` or `requirements_test.txt`

**Example:**

```json
// manifest.json
{
  "requirements": ["aiohttp>=3.8.0"]
}
```

```txt
# requirements.txt
aiohttp>=3.8.0
```

## 🚀 Bootstrap Script

`script/setup/bootstrap` creates the virtual environment and installs everything needed to run and test the integration.

### From this project

1. `requirements_dev.txt` - development tools (pyright, ruff, codespell, pre-commit, colorlog, performance packages)
2. `requirements_test.txt` - `pytest-homeassistant-custom-component`, which pulls in Home Assistant itself plus the full pytest stack
3. `requirements.txt` - this integration's runtime dependencies (currently none)

Home Assistant is **not** pinned directly. It arrives as a transitive dependency of
`pytest-homeassistant-custom-component`, which keeps the Home Assistant version and the Python
version constraints consistent between local development and CI.

### From the installed Home Assistant

4. **Base component requirements**, resolved by `script/setup/ha-base-requirements`

   Home Assistant installs a component's `requirements` when that component is *set up*. But
   `homeassistant.helpers.service._base_components()` *imports* ~19 entity components
   (`ai_task`, `camera`, `climate`, `cover`, `light`, `media_player`, `notify`, ...) to validate
   service call schemas, and those modules import their own dependencies at module level. In a
   minimal dev config none of them is ever set up, so nobody installs their packages. One missing
   package raises `ModuleNotFoundError` inside the websocket handler, the frontend only sees
   `{"code": "unknown_error"}`, and onboarding hangs forever on "Loading data".

   `script/setup/ha-base-requirements` derives these packages from the *installed* Home Assistant
   instead of hardcoding them:

   - it reads the component list out of `helpers/service.py` with `ast`
   - it follows each component's `manifest.json` `dependencies` recursively
   - it prints the union of their already-pinned `requirements`

   For Home Assistant 2026.2.3 that resolves to `PyTurboJPEG`, `av`, `ha-ffmpeg`, `hassil`,
   `home-assistant-intents`, `mutagen`, `numpy`, `pymicro-vad` and `pyspeex-noise`. Because the
   list is derived rather than pinned, a Home Assistant upgrade does not silently reintroduce the
   bug. Run it by hand to see where each package comes from:

   ```bash
   script/setup/ha-base-requirements --explain
   ```

To check that the environment is complete:

```bash
python3 -c "from homeassistant.helpers.service import _base_components; print(len(_base_components()))"
```

It must print the number of base components (19 on Home Assistant 2026.2.3) without raising.

## 🔍 hacs.json vs manifest.json

### hacs.json

```json
{
  "name": "Integration Name",
  "homeassistant": "2026.11.0",
  "hacs": "2.0.5"
}
```

- ❌ **No Python dependencies** - only metadata
- ✅ Minimum Home Assistant version
- ✅ Minimum HACS version

### manifest.json

```json
{
  "requirements": ["package>=1.0.0"]
}
```

- ✅ **Python package dependencies**
- ✅ Installed by Home Assistant

**No duplication needed!** `hacs.json` only contains version constraints for HA/HACS, not Python packages.
