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

class ClassChartsHomeworkCalendar(CoordinatorEntity, CalendarEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Homework"
        self._attr_unique_id = f"{entry.entry_id}_homework"

    def _get_events(self) -> list[CalendarEvent]:
        events = []
        hw_data = self.coordinator.data.get("homework", {})
        hw_list = hw_data.get("data", []) if isinstance(hw_data, dict) else []
        
        for hw in hw_list:
            try:
                due = date.fromisoformat(hw["due_date"])
                events.append(CalendarEvent(
                    summary=f"HW: {hw.get('subject')}",
                    start=due, end=due + timedelta(days=1),
                    description=hw.get("description", "")
                ))
            except: continue
        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date):
        return [e for e in self._get_events() if e.start >= start_date.date() and e.start <= end_date.date()]
