"""Constants for smart_venetian_blinds."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# Integration metadata
DOMAIN = "smart_venetian_blinds"
ATTRIBUTION = "Sun-based slat angle calculation"

# Platform parallel updates - applied to all platforms
PARALLEL_UPDATES = 1

# Sun entity IDs
SENSOR_SUN_AZIMUTH = "sensor.sun_solar_azimuth"
SENSOR_SUN_ELEVATION = "sensor.sun_solar_elevation"
SUN_ENTITY = "sun.sun"

# Subentry type
SUBENTRY_TYPE_COVER = "cover"

# === GROUP CONFIG KEYS (entry.data) ===
CONF_GROUP_NAME = "name"
CONF_FACADE_AZIMUTH = "facade_azimuth_deg"
CONF_SLAT_WIDTH = "slat_width_mm"
CONF_SLAT_SPACING = "slat_spacing_mm"

# === GROUP OPTIONS KEYS (entry.options) ===
CONF_CHANGE_THRESHOLD = "change_threshold_deg"
CONF_MIN_UPDATE_INTERVAL = "min_update_interval_sec"

# === COVER SUBENTRY KEYS (subentry.data) ===
CONF_COVER_ENTITY = "cover_entity_id"
CONF_COVER_NAME = "name"
CONF_DRIVE_POSITION = "drive_position"
CONF_MIN_ANGLE = "min_angle_deg"
CONF_MAX_ANGLE = "max_angle_deg"
CONF_INVERT_TILT = "invert_tilt_percent"
CONF_NO_SUN_BEHAVIOR = "no_sun_behavior"
CONF_NO_SUN_POSITION = "no_sun_position_percent"
CONF_RESPECT_MANUAL_CLOSE = "respect_manual_close"
CONF_MANUAL_CLOSE_THRESHOLD = "manual_close_threshold_percent"
CONF_MINIMUM_TILT_CHANGE = "minimum_tilt_change_percent"
CONF_COVER_ENABLED = "enabled"

# === DEFAULTS ===
DEFAULT_DRIVE_POSITION = 100
DEFAULT_MIN_ANGLE = 0
DEFAULT_MAX_ANGLE = 90
DEFAULT_INVERT_TILT = False
DEFAULT_NO_SUN_BEHAVIOR = "keep_last"
DEFAULT_NO_SUN_POSITION = 50
DEFAULT_RESPECT_MANUAL_CLOSE = True
DEFAULT_MANUAL_CLOSE_THRESHOLD = 30
DEFAULT_MINIMUM_TILT_CHANGE = 5
DEFAULT_COVER_ENABLED = True
DEFAULT_CHANGE_THRESHOLD = 5
DEFAULT_MIN_UPDATE_INTERVAL = 60
DEFAULT_SLAT_WIDTH = 80
DEFAULT_SLAT_SPACING = 70
DEFAULT_FACADE_AZIMUTH = 180
