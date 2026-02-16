# Architectural and Design Decisions

This document records significant architectural and design decisions made during the development of this integration.

## Format

Each decision is documented with:

- **Date:** When the decision was made
- **Context:** Why this decision was necessary
- **Decision:** What was decided
- **Rationale:** Why this approach was chosen
- **Consequences:** Expected impacts and trade-offs

---

## Decision Log

### Event-Driven Updates via Sun Entity

**Context:** The integration needs to react to changing sun position throughout the day. Options include polling on a timer or listening for sun entity state changes.

**Decision:** Listen for `sun.sun` (or dedicated solar sensor) state changes via `SunStateListener` rather than polling on a fixed interval.

**Rationale:**

- Sun position changes at a natural rate — no need to poll
- Avoids unnecessary computation when sun hasn't moved
- Reduces resource usage compared to fixed-interval polling
- Home Assistant's sun integration already handles astronomical calculations

**Consequences:**

- Update frequency is determined by HA's sun entity update rate
- Integration depends on the `sun` integration being loaded
- Debouncing needed to avoid rapid-fire updates during state transitions

---

### Local Calculation, No External API

**Context:** The integration needs to determine optimal slat angles. This could be done via an external service or computed locally.

**Decision:** All slat angle calculations are performed locally using sun position, facade azimuth, and slat geometry. No external API is used.

**Rationale:**

- Deterministic math based on geometry — no cloud dependency needed
- Zero latency for calculations
- Works offline and without internet
- No API keys, rate limits, or service outages to worry about

**Consequences:**

- IoT class is `calculated`
- All math lives in `sun/math.py` and must be well-tested
- No `aiohttp` or network dependencies needed

---

### Window Groups as Config Entries, Covers as Subentries

**Context:** Users may have multiple windows with different facade orientations. Each window may have multiple physical covers (e.g., left and right blinds on the same wall).

**Decision:** Model window groups as config entries (sharing facade azimuth and slat geometry) and individual covers as subentries within each group.

**Rationale:**

- Groups share physical parameters (facade direction, slat dimensions) — avoids duplication
- Subentries allow per-cover settings (entity ID, tilt inversion, drive position)
- Aligns with Home Assistant's config entry / subentry model
- Clean separation between group-level and cover-level configuration

**Consequences:**

- Each group gets its own coordinator instance
- Covers within a group all receive the same calculated angle
- Adding/removing covers doesn't require reconfiguring the group

---

### Drive-Then-Tilt Pattern

**Context:** Some cover hardware requires being driven to a specific position before tilt can be applied. Sending tilt directly may not work if the cover is fully closed or in an unexpected position.

**Decision:** `CoverController` implements a two-step process: first drive the cover to a configurable position, then apply the calculated tilt angle.

**Rationale:**

- Ensures tilt commands work reliably across different cover hardware
- Drive position is configurable per cover to handle hardware differences
- Some covers need to be partially open before tilt has effect

**Consequences:**

- Small delay between drive and tilt commands
- Drive position must be configured correctly per cover
- More complex than a single tilt command

---

### One-Shot No-Sun Action

**Context:** When the sun is not hitting the facade (below horizon, behind the building), the integration can either leave the blinds alone or apply a configured action (open fully, or apply reflection protection angle).

**Decision:** The no-sun action is applied once when the sun leaves the facade, then not repeated until the sun hits the facade again.

**Rationale:**

- Prevents repeatedly driving covers to the same position
- Allows users to manually adjust blinds after the no-sun action fires
- The `no_sun_action_applied` flag resets when sun hits the facade again

**Consequences:**

- If user manually changes blinds after no-sun action, the integration won't override them until next sun cycle
- State tracking required in `GroupState` (`no_sun_action_applied`, `sun_has_hit_facade`)

---

### Manual Close Detection (Sleep Mode)

**Context:** Users may manually close their blinds (e.g., for sleeping) and don't want the integration to reopen them when the sun changes position.

**Decision:** Each cover has a configurable close detection threshold. If the cover position is below this threshold, auto-control skips that cover.

**Rationale:**

- Respects user intent when blinds are manually closed
- Threshold is configurable to account for different "closed" positions across hardware
- Simple position-based check — no complex intent detection

**Consequences:**

- Cover positions must be tracked in `GroupState`
- Threshold must be set appropriately per cover hardware
- User must manually reopen or toggle auto-control to resume automation

---

### DataUpdateCoordinator for State Management

**Context:** The integration needs to compute and distribute slat angle data to multiple sensor entities per group.

**Decision:** Use Home Assistant's `DataUpdateCoordinator` as the central state management component, even though updates are event-driven rather than polled.

**Rationale:**

- Provides built-in entity availability tracking
- Standard pattern recommended by Home Assistant
- Shared data access prevents duplicate calculations
- Entities automatically become unavailable when coordinator fails

**Consequences:**

- All entities must inherit from `CoordinatorEntity`
- Coordinator is triggered by sun listener events, not by its own polling interval

---

### EntityDescription for Static Metadata

**Context:** Entities have static metadata (name, icon, device class) that doesn't change.

**Decision:** Use `EntityDescription` dataclasses to define static entity metadata.

**Rationale:**

- Declarative and easy to read
- Type-safe with dataclasses
- Recommended Home Assistant pattern
- Separates static configuration from dynamic behavior

**Consequences:**

- Each entity type needs an EntityDescription
- Static and dynamic properties clearly separated

---

### Services Registered in async_setup, Not async_setup_entry

**Context:** Service actions (like `apply_now`) need to be registered once for the integration, not per config entry.

**Decision:** Register all services in `async_setup()` at integration level, not in `async_setup_entry()`.

**Rationale:**

- Services are integration-wide, not entry-specific
- Prevents duplicate registration when multiple groups are configured
- Follows Home Assistant best practices

**Consequences:**

- Services must look up the correct entry/coordinator from their call data
- Service registration happens once at integration load time

---

## Decision Review

These decisions should be reviewed periodically (suggested: quarterly or when major features are added) to ensure they still serve the integration's needs.
