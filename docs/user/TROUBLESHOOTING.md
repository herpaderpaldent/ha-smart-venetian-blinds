# Troubleshooting & Best Practices

## Sunlight Coming Through the Blinds

If you see fine lines of sunlight penetrating your blinds, check these common causes:

### 1. Verify Slat Measurements

The calculation depends critically on accurate slat geometry:

**Slat Width (L)** - Measure the actual width of each slat from edge to edge (the dimension that blocks light when closed).

**Slat Spacing (d)** - Measure from the **bottom edge of one slat to the bottom edge of the next slat** (not the gap between slats).

```
    +==============+  <- slat top
    |   slat (L)   |  <- slat width = full slat dimension
    +==============+  <- slat bottom
          | gap
    +==============+
    |   slat (L)   |  <- spacing (d) = bottom-to-bottom
    +==============+
```

**Common mistakes:**

- Measuring only the visible gap instead of bottom-to-bottom spacing
- Measuring slat width at an angle instead of straight across
- Using nominal values from spec sheets instead of actual measurements

**Why it matters:** The formula `sin(theta + omega) = (d * cos(omega)) / L` requires precise values. If `d/L > 1`, complete sun blocking is physically impossible.

### 2. Reduce Minimum Tilt Change Threshold

The default 5% threshold prevents motor wear but can cause the blinds to lag behind the sun:

| Threshold    | Tracking Precision | Motor Activity |
| ------------ | ------------------ | -------------- |
| 5% (default) | +/-5% drift        | Low            |
| 2%           | +/-2% drift        | Medium         |
| 0%           | Optimal tracking   | Higher         |

**Recommendation:** If you see sunlight leaking, try reducing to **2%** or **1%**. This allows the blinds to track the sun more precisely.

To change: Reconfigure the cover -> "Minimum tilt change" setting.

### 3. Check Your Geometry Ratio

The integration calculates a ratio: `(spacing * cos(profile_angle)) / width`

- **Ratio <= 1.0**: Full sun blocking possible
- **Ratio > 1.0**: Sun will penetrate regardless of slat angle

If your slats are spaced far apart relative to their width, sunlight will always penetrate at certain sun angles (especially low morning/evening sun).

**Solutions for unfavorable geometry:**

- Accept that some sun penetration is unavoidable
- Consider blinds with wider slats or tighter spacing
- Use the "no sun behavior" setting to fully close during problematic times

### 4. Monitor the Diagnostic Sensors

The integration provides sensors to help diagnose issues:

- `sensor.<group>_slat_angle` - Target angle in degrees
- `sensor.<group>_slat_tilt` - Target tilt in percent
- `sensor.<group>_profile_angle` - Vertical sun angle on facade (disabled by default - enable in entity settings)

Check if the slat_tilt sensor shows the value you expect. If the sensor shows the correct value but blinds aren't there, the minimum tilt threshold may be blocking updates.

### 5. Facade Azimuth Accuracy

The facade azimuth (compass direction your window faces) affects all calculations:

- **0 deg** = North
- **90 deg** = East
- **180 deg** = South
- **270 deg** = West

**This is especially critical when sun comes from the side.** The Horizontal Shadow Angle (HSA) = Sun Azimuth - Facade Azimuth. When HSA is large (sun at an angle to the facade), even small errors in facade azimuth cause large calculation errors.

How to verify:

1. Use a compass app standing at the window, facing outward
2. Or measure from Google Maps aerial view
3. **Test:** When calculated tilt is very wrong, check if your facade azimuth is off by 20-40 deg

### 6. Diagnostic Template

Run this in **Developer Tools -> Template** when sun is penetrating:

```jinja
{# Replace YOUR_GROUP_NAME with your actual group name (e.g., "living_room") #}
{% set group = "YOUR_GROUP_NAME" %}
=== SUN POSITION ===
Azimuth: {{ state_attr('sun.sun', 'azimuth') }}deg
Elevation: {{ state_attr('sun.sun', 'elevation') }}deg

=== CALCULATED VALUES ===
Profile Angle: {{ states('sensor.' ~ group ~ '_profile_angle') }}deg
Slat Angle: {{ states('sensor.' ~ group ~ '_slat_angle') }}deg
Slat Tilt: {{ states('sensor.' ~ group ~ '_slat_tilt') }}%

=== YOUR COVER ===
{# Replace YOUR_COVER with your cover entity id #}
Cover Tilt: {{ state_attr('cover.YOUR_COVER', 'current_tilt_position') }}%

=== MANUAL CALCULATION ===
{# Enter your configured values here #}
{% set facade_azimuth = 180 %}  {# Your facade azimuth #}
{% set slat_width = 80 %}       {# Your slat width in mm #}
{% set slat_spacing = 70 %}     {# Your slat spacing in mm #}

HSA (Horizontal Shadow Angle): {{ (state_attr('sun.sun', 'azimuth')|float - facade_azimuth)|round(1) }}deg
Geometry Ratio (d/L): {{ (slat_spacing / slat_width)|round(3) }}
```

**Key diagnostics:**

- If HSA is large (>60 deg) and calculation seems wrong, your facade azimuth may be misconfigured
- If Geometry Ratio > 1, sun penetration is physically unavoidable at some angles
- Compare "Slat Tilt" sensor vs "Cover Tilt" - if different, the minimum threshold may be blocking updates

## Quick Diagnostic Checklist

- [ ] Measured slat width with ruler (mm)
- [ ] Measured slat spacing bottom-to-bottom (mm)
- [ ] Verified facade azimuth with compass
- [ ] Checked minimum tilt change threshold (try 2%)
- [ ] Ran diagnostic template during sunlight leakage
- [ ] Compared calculated tilt vs. manually-working tilt

## Debug Logging

Enable debug logging to see detailed calculation steps:

```yaml
logger:
  default: warning
  logs:
    custom_components.smart_venetian_blinds: debug
```

Add this to `configuration.yaml` and restart Home Assistant. The logs will show:

- Sun position updates
- Calculated angles and why
- Why tilt changes were applied or skipped

## Getting Help

If you've followed this guide and still have issues:

1. Collect the diagnostic template output when the problem occurs
2. Note what tilt percentage actually blocks the sun (test manually)
3. [Open an issue](https://github.com/herpaderpaldent/ha-smart-venetian-blinds/issues) with this information
