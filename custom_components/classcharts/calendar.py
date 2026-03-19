from __future__ import annotations
from datetime import datetime, date, timedelta

from homeassistant.util import dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Class Charts calendars."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        ClassChartsTimetableCalendar(coordinator, entry),
        ClassChartsHomeworkCalendar(coordinator, entry),
    ])

class ClassChartsCalendarBase(CoordinatorEntity, CalendarEntity):
    """Base class for Class Charts calendars."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{self.calendar_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Class Charts",
        }

class ClassChartsTimetableCalendar(ClassChartsCalendarBase):
    """Calendar for school lessons."""
    calendar_type = "timetable"
    _attr_name = "Class Charts Timetable"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        events = self._get_events()
        now = dt_util.now()
        upcoming = [e for e in events if e.end > now]
        return upcoming[0] if upcoming else None

    def _get_events(self) -> list[CalendarEvent]:
        """Convert coordinator timetable data to CalendarEvents."""
        events = []
        # Specifically pull the timetable dictionary
        data = self.coordinator.data.get("timetable", {})
        
        # Shield: If data is a list (causing your error), stop here and return empty
        if not isinstance(data, dict):
            return []

        for date_str, lessons in data.items():
            for lesson in lessons:
                try:
                    # Parse strings and convert to local time for HA
                    start_dt = datetime.fromisoformat(lesson["start_time"])
                    end_dt = datetime.fromisoformat(lesson["end_time"])
                    
                    events.append(
                        CalendarEvent(
                            summary=lesson.get("subject_name", "Unknown"),
                            start=dt_util.as_local(start_dt),
                            end=dt_util.as_local(end_dt),
                            location=lesson.get("room_name"),
                            description=f"Teacher: {lesson.get('teacher_name')}",
                        )
                    )
                except (KeyError, ValueError, TypeError):
                    continue
        
        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return events within a specific time range for the UI."""
        all_events = self._get_events()
        return [
            e for e in all_events 
            if e.start >= start_date and e.end <= end_date
        ]

class ClassChartsHomeworkCalendar(ClassChartsCalendarBase):
    """Calendar for homework due dates."""
    calendar_type = "homework"
    _attr_name = "Class Charts Homework"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next homework due."""
        events = self._get_events()
        now = dt_util.now()
        upcoming = [e for e in events if e.start >= now.date()]
        return upcoming[0] if upcoming else None

    def _get_events(self) -> list[CalendarEvent]:
        """Convert coordinator homework list to CalendarEvents."""
        events = []
        hw_raw = self.coordinator.data.get("homework", {})
        
        # Homework is usually a list inside a 'data' key
        homework_list = hw_raw.get("data", []) if isinstance(hw_raw, dict) else []
        
        if not isinstance(homework_list, list):
            return []

        for hw in homework_list:
            try:
                # Homework events are 'All Day'
                due_date = date.fromisoformat(hw.get("due_date"))
                
                events.append(
                    CalendarEvent(
                        summary=f"HW: {hw.get('subject', 'Assignment')}",
                        start=due_date,
                        # HA All-Day events MUST end on the next day
                        end=due_date + timedelta(days=1),
                        description=hw.get("description", ""),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
                
        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        all_events = self._get_events()
        return [
            e for e in all_events 
            if e.start >= start_date.date() and e.start <= end_date.date()
        ]
