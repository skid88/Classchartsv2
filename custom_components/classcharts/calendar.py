from __future__ import annotations
from datetime import datetime, date, timedelta
from homeassistant.util import dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ClassChartsTimetableCalendar(coordinator, entry),
        ClassChartsHomeworkCalendar(coordinator, entry),
    ])

class ClassChartsTimetableCalendar(CoordinatorEntity, CalendarEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{entry.entry_id}_timetable"

    @property
    def event(self) -> CalendarEvent | None:
        events = self._get_events()
        now = dt_util.now()
        upcoming = [e for e in events if e.end > now]
        return upcoming[0] if upcoming else None

    def _get_events(self) -> list[CalendarEvent]:
        events = []
        data = self.coordinator.data.get("timetable", {})
        if not isinstance(data, dict): return []

        for date_str, lessons in data.items():
            for lesson in lessons:
                try:
                    start = dt_util.as_local(datetime.fromisoformat(lesson["start_time"]))
                    end = dt_util.as_local(datetime.fromisoformat(lesson["end_time"]))
                    events.append(CalendarEvent(
                        summary=lesson["subject_name"],
                        start=start, end=end,
                        location=lesson.get("room_name"),
                        description=f"Teacher: {lesson.get('teacher_name')}"
                    ))
                except: continue
        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date):
        return [e for e in self._get_events() if e.start >= start_date and e.end <= end_date]

class ClassChartsHomeworkCalendar(ClassChartsCalendarBase):
    """Calendar for homework due dates."""
    calendar_type = "homework"
    _attr_name = "Class Charts Homework"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next homework due."""
        events = self._get_events()
        # Get today's date
        now_date = dt_util.now().date()
        
        # Find homework that is due today or in the future
        upcoming = [e for e in events if e.start >= now_date]
        return upcoming[0] if upcoming else None

    def _get_events(self) -> list[CalendarEvent]:
        """Convert coordinator homework list to CalendarEvents."""
        events = []
        hw_raw = self.coordinator.data.get("homework", {})
        
        # Class Charts puts the actual list inside a 'data' key
        homework_list = hw_raw.get("data", []) if isinstance(hw_raw, dict) else []
        
        if not isinstance(homework_list, list):
            return []

        for hw in homework_list:
            try:
                # Homework usually only has a due date (YYYY-MM-DD)
                due_date = date.fromisoformat(hw.get("due_date"))
                
                events.append(
                    CalendarEvent(
                        summary=f"HW: {hw.get('subject', 'Assignment')}",
                        start=due_date,
                        # All-day events in HA must end on the following day
                        end=due_date + timedelta(days=1),
                        description=hw.get("description", ""),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
                
        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return events for the calendar UI view."""
        all_events = self._get_events()
        return [
            e for e in all_events 
            if e.start >= start_date.date() and e.start <= end_date.date()
        ]
