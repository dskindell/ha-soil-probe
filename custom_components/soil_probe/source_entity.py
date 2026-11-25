"""Base for the probe's entities that follow one source entity's state."""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, EventStateReportedData, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_state_report_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .calibration import reading_of
from .const import CONF_STALE_MINUTES, calibration_signal
from .device import probe_device_info

_STALE_CHECK = timedelta(seconds=30)


class SourceEntity(Entity):
    """Follows a source entity; a missing, unusable or stale reading is passed on as None."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, key: str, source: str) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = probe_device_info(entry)
        self._source = source

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(self.hass, self._source, self._source_changed)
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, calibration_signal(self._entry.entry_id), self._refresh
            )
        )
        # A repeated value is reported, not changed; it still counts against the timeout.
        self.async_on_remove(
            async_track_state_report_event(self.hass, self._source, self._source_reported)
        )
        self.async_on_remove(async_track_time_interval(self.hass, self._check_stale, _STALE_CHECK))
        self._update(self.hass.states.get(self._source))

    @callback
    def _source_changed(self, event: Event[EventStateChangedData]) -> None:
        self._update(event.data["new_state"])
        self.async_write_ha_state()

    @callback
    def _refresh(self) -> None:
        self._update(self.hass.states.get(self._source))
        self.async_write_ha_state()

    @callback
    def _source_reported(self, _event: Event[EventStateReportedData]) -> None:
        self._check_stale()

    @callback
    def _check_stale(self, _now: datetime | None = None) -> None:
        was_available = self._attr_available
        self._update(self.hass.states.get(self._source))
        if self._attr_available != was_available:
            self.async_write_ha_state()

    @callback
    def _update(self, state: State | None) -> None:
        reading = reading_of(state)
        self._apply(None if reading is None or self._stale(state) else reading)

    def _stale(self, state: State | None) -> bool:
        minutes = self._entry.options.get(CONF_STALE_MINUTES, 0)
        # last_reported also moves when a source repeats the same value.
        return (
            state is not None
            and minutes > 0
            and dt_util.utcnow() - state.last_reported > timedelta(minutes=minutes)
        )

    @abstractmethod
    def _apply(self, reading: float | None) -> None:
        """Set the entity's state from the source reading, or None when there is none."""
