from __future__ import annotations
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # We define the entities here
    async_add_entities([
        CCHomeworkSensor(coordinator, entry, "outstanding", "this_week_outstanding_count"),
        CCLessonSensor(coordinator, entry, "current"),
        CCLessonSensor(coordinator, entry, "next")
    ])

class CCHomeworkSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Homework counts."""
    def __init__(self, coordinator, entry, name, key):
        super().__init__(coordinator)
        self._attr_name = f"Homework {name.capitalize()}"
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_hw_{name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Class Charts",
        }

    @property
    def native_value(self):
        """Return the count from the coordinator data."""
        hw = self.coordinator.data.get("homework", {})
        # Safety check for nested dictionary
        meta = hw.get("meta", {}) if isinstance(hw, dict) else {}
        return meta.get(self._key, 0)

class CCLessonSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Current and Next lessons."""
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
        """Calculate the current or next lesson based on the clock."""
        now = dt_util.now()
        today_str = now.strftime("%Y-%m-%d")
        
        # Get today's list from the dictionary of dates
        timetable = self.coordinator.data.get("timetable", {})
        today_lessons = timetable.get(today_str, [])
        
        parsed = []
        for l in today_lessons:
            try:
                # Convert strings to timezone-aware datetimes
                start_naive = datetime.fromisoformat(l["start_time"])
                end_naive = datetime.fromisoformat(l["end_time"])
                
                l["dt_start"] = dt_util.as_local(start_naive)
                l["dt_end"] = dt_util.as_local(end_naive)
                parsed.append(l)
            except (KeyError, ValueError, TypeError):
                continue
        
        # Ensure they are in chronological order
        parsed.sort(key=lambda x: x["dt_start"])
        
        if self._type == "current":
            for l in parsed:
                if l["dt_start"] <= now <= l["dt_end"]:
                    return l["subject_name"]
        
        elif self._type == "next":
            for l in parsed:
                if l["dt_start"] > now:
                    return l["subject_name"]
                    
        return "Free"
