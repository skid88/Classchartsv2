from __future__ import annotations
from datetime import datetime, date, timedelta

from homeassistant.util import dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

def clean_html_tags(raw_html: str) -> str:
    """Strip HTML tags and unescape HTML entities."""
    if not raw_html:
        return ""
    import re
    import html
    text = html.unescape(raw_html)
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'\n\s*\n', '\n', clean_text)
    return clean_text.strip()

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts calendars."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ClassChartsTimetableCalendar(coordinator, entry),
        ClassChartsHomeworkCalendar(coordinator, entry),
    ])

class ClassChartsTimetableCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar for school lessons."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{entry.entry_id}_timetable"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Class Charts",
        }

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming lesson."""
        events = self._get_events()
        now = dt_util.now()
        upcoming = [e for e in events if e.end > now]
        return upcoming[0] if upcoming else None

    def _get_events(self) -> list[CalendarEvent]:
        """Convert coordinator data to CalendarEvents."""
        events = []
        
        # --- Part A: Handle Timetable Lessons ---
        timetable_data = self.coordinator.data.get("timetable", {})
        if isinstance(timetable_data, dict):
            for date_str, lessons in timetable_data.items():
                for lesson in lessons:
                    try:
                        start = dt_util.as_local(datetime.fromisoformat(lesson["start_time"]))
                        end = dt_util.as_local(datetime.fromisoformat(lesson["end_time"]))
                        events.append(CalendarEvent(
                            summary=lesson.get("subject_name", "Unknown"),
                            start=start,
                            end=end,
                            location=lesson.get("room_name"),
                            description=f"Teacher: {lesson.get('teacher_name')}"
                        ))
                    except (KeyError, ValueError, TypeError):
                        continue

        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return events for the UI."""
        all_events = self._get_events()
        # Lessons are datetimes, so compare directly with start_date/end_date
        return [
            e for e in all_events 
            if e.start >= start_date and e.end <= end_date
        ]

class ClassChartsHomeworkCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar for homework due dates."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Homework"
        self._attr_unique_id = f"{entry.entry_id}_homework"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Class Charts",
        }

    @property
    def _get_events(self) -> list[CalendarEvent]:
        """Convert coordinator homework list to CalendarEvents."""
        events = []
        hw_raw = self.coordinator.data.get("homework", {})
        
        # Handle the nested 'data' list from ClassCharts API
        homework_list = hw_raw.get("data", []) if isinstance(hw_raw, dict) else []
        
        for hw in homework_list:
            try:
                due_date = date.fromisoformat(hw.get("due_date"))
                
                # Check completion status from the API
                is_completed = hw.get("status", {}).get("ticked") == "yes"

                event = CalendarEvent(
                    summary=f"HW: {hw.get('subject', 'Assignment')}",
                    start=due_date,
                    end=due_date + timedelta(days=1),
                    description=clean_html_tags(hw.get("description", "")),
                )
                
                # Attach the completion status for the filter
                event.is_completed_homework = is_completed
                events.append(event)
            except (KeyError, ValueError, TypeError):
                continue
                
        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return events for the calendar UI view with filtering."""
        # Pull from .options, not .data
        show_completed = self.coordinator.config_entry.options.get("show_completed_homework", True)
        
        all_events = self._get_events()
        return [
            e for e in all_events 
            if e.start >= start_date.date() and e.start <= end_date.date()
            and (show_completed or not getattr(e, "is_completed_homework", False))
        ]
