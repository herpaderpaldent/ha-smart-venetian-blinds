"""
Persistent record of the one-time season rest drive.

When a group enters its seasonal pause, each cover is driven once to the rest
position. That "already done" fact has to outlive a Home Assistant restart —
otherwise a restart mid-pause would either re-drive a cover the user has since
moved by hand, or silently cancel a drive that never happened.

The record is keyed by cover entity id and carries the window it belongs to, so
editing the season or the rest position during a pause re-arms the drive.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from custom_components.smart_venetian_blinds.const import DOMAIN, LOGGER
from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.season.window import SeasonWindow
    from homeassistant.core import HomeAssistant

STORAGE_VERSION = 1
SAVE_DELAY_SECONDS = 5

KEY_IDENTITY = "identity"
KEY_PENDING_SINCE = "pending_since"
KEY_DONE = "done"


class SeasonRestStore:
    """
    Tracks, per cover, whether the season rest drive has already run.

    A record is only honoured while it belongs to the current pause period and to
    the current season settings. Anything older is treated as "not done yet".
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the store for one window group."""
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.season")
        self._data: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        """Load the persisted records."""
        stored = await self._store.async_load()
        self._data = dict(stored or {})

    async def async_remove(self) -> None:
        """Delete the persisted records (called when the group is removed)."""
        await self._store.async_remove()

    def _schedule_save(self) -> None:
        """Persist the current records shortly."""
        self._store.async_delay_save(lambda: self._data, SAVE_DELAY_SECONDS)

    def _current_record(self, entity_id: str, season: SeasonWindow, today: date) -> dict[str, Any] | None:
        """Return the record for the pause period containing ``today``, if any."""
        record = self._data.get(entity_id)
        if record is None or record.get(KEY_IDENTITY) != season.identity:
            return None

        period_start = season.pause_period_start(today)
        if period_start is None:
            return None

        try:
            pending_since = date.fromisoformat(str(record[KEY_PENDING_SINCE]))
        except (KeyError, ValueError):
            return None

        return record if pending_since >= period_start else None

    def is_done(self, entity_id: str, season: SeasonWindow, today: date) -> bool:
        """Return True if the rest drive already ran (or was given up on) this pause."""
        record = self._current_record(entity_id, season, today)
        return bool(record and record.get(KEY_DONE))

    def pending_since(self, entity_id: str, season: SeasonWindow, today: date) -> date:
        """
        Return the day this pause's rest drive became pending, starting it if needed.

        Args:
            entity_id: The cover entity.
            season: The group's season window.
            today: Today's date in Home Assistant's timezone.

        Returns:
            The date the drive was first found pending.
        """
        record = self._current_record(entity_id, season, today)
        if record is None:
            self._data[entity_id] = {
                KEY_IDENTITY: season.identity,
                KEY_PENDING_SINCE: today.isoformat(),
                KEY_DONE: None,
            }
            self._schedule_save()
            return today

        return date.fromisoformat(str(record[KEY_PENDING_SINCE]))

    def mark_done(self, entity_id: str, season: SeasonWindow, today: date) -> None:
        """Record that the rest drive ran, or was abandoned, for this pause."""
        record = self._data.setdefault(
            entity_id,
            {KEY_IDENTITY: season.identity, KEY_PENDING_SINCE: today.isoformat(), KEY_DONE: None},
        )
        record[KEY_IDENTITY] = season.identity
        record[KEY_DONE] = today.isoformat()
        self._schedule_save()
        LOGGER.debug("Cover %s: season rest drive recorded as done for %s", entity_id, season.identity)

    def as_diagnostics(self) -> dict[str, Any]:
        """Return the raw records for the diagnostics download."""
        return dict(self._data)


__all__ = [
    "SeasonRestStore",
]
