from __future__ import annotations
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # These must be indented INSIDE this function
    async_add_entities([
        # Homework Entities (3)
        CCHomeworkSensor(coordinator, entry, "Outstanding Homework", "this_week_outstanding_count"),
        CCHomeworkSensor(coordinator, entry, "Homework Due", "this_week_due_count"),
        CCHomeworkSensor(coordinator, entry, "Completed Homework", "this_week_completed_count"),
        
        # Lesson Entities (2)
        CCLessonSensor(coordinator, entry, "current"),
        CCLessonSensor(coordinator, entry, "next")
    ])

class CCHomeworkSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Homework stats."""
    def __init__(self, coordinator, entry, name, key):
        super().__init__(coordinator)
        self._attr_name = name
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_hw_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Class Charts",
        }

    @property
    def native_value(self):
        hw = self.coordinator.data.get("homework", {})
        meta = hw.get("meta", {}) if isinstance(hw, dict) else {}
        return meta.get(self._key, 0)

class CCLessonSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Lessons."""
    def __init__(self, coordinator, entry, type):
        super().__init__(coordinator)
        self._type = type
        self._attr_name = f"Class Charts {type.capitalize()} Lesson"
        self._attr_unique_id = f"{entry.entry_id}_lesson_{type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Class Charts",
        }

    @property
    def native_value(self):
        now = dt_util.now()
        today_str = now.strftime("%Y-%m-%d")
        timetable = self.coordinator.data.get("timetable", {})
        today_lessons = timetable.get(today_str, [])
        
        parsed = []
        for l in today_lessons:
            try:
                start_naive = datetime.fromisoformat(l["start_time"])
                end_naive = datetime.fromisoformat(l["end_time"])
                l["dt_start"] = dt_util.as_local(start_naive)
                l["dt_end"] = dt_util.as_local(end_naive)
                parsed.append(l)
            except:
                continue
        
        parsed.sort(key=lambda x: x["dt_start"])
        
        if self._type == "current":
            for l in parsed:
                if l["dt_start"] <= now <= l["dt_end"]:
                    return l["subject_name"]
        else:
            for l in parsed:
                if l["dt_start"] > now:
                    return l["subject_name"]
                    
        return "Free"
