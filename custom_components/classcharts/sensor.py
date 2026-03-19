from __future__ import annotations
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        CCHomeworkSensor(coordinator, entry, "outstanding", "this_week_outstanding_count"),
        CCLessonSensor(coordinator, entry, "current"),
        CCLessonSensor(coordinator, entry, "next")
    ])

class CCHomeworkSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, name, key):
        super().__init__(coordinator)
        self._attr_name = f"Homework {name.capitalize()}"
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_hw_{name}"

    @property
    def native_value(self):
        hw = self.coordinator.data.get("homework", {})
        return hw.get("meta", {}).get(self._key, 0)

class CCLessonSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, type):
        super().__init__(coordinator)
        self._type = type
        self._attr_name = f"Class Charts {type.capitalize()} Lesson"
        self._attr_unique_id = f"{entry.entry_id}_lesson_{type}"

    @property
    def native_value(self):
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        today_lessons = self.coordinator.data.get("timetable", {}).get(today_str, [])
        
        parsed = []
        for l in today_lessons:
            try:
                l["dt_start"] = datetime.fromisoformat(l["start_time"])
                l["dt_end"] = datetime.fromisoformat(l["end_time"])
                parsed.append(l)
            except: continue
        
        parsed.sort(key=lambda x: x["dt_start"])
        
        if self._type == "current":
            for l in parsed:
                if l["dt_start"] <= now <= l["dt_end"]:
                    return l["subject_name"]
        else: # next
            for l in parsed:
                if l["dt_start"] > now:
                    return l["subject_name"]
                    
        return "Free"
