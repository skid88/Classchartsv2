import logging
import datetime
from datetime import timedelta
import requests

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import (
    DOMAIN, 
    LOGIN_URL, 
    TIMETABLE_URL, 
    CONF_PUPIL_ID,
    CONF_REFRESH_INTERVAL,
    CONF_DAYS_TO_FETCH
)

_LOGGER = logging.getLogger(__name__)

def _normalize_lesson(lesson):
    if not isinstance(lesson, dict):
        return {}
    subject = lesson.get("subject") or {}
    teacher = lesson.get("teacher") or {}
    room = lesson.get("room") or {}
    return {
        "subject_name": lesson.get("subject_name") or subject.get("name"),
        "teacher_name": lesson.get("teacher_name") or teacher.get("name"),
        "room_name": lesson.get("room_name") or room.get("name"),
        "start_time": lesson.get("start_time") or lesson.get("start"),
        "end_time": lesson.get("end_time") or lesson.get("end"),
        "raw": lesson,
    }

def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    """Fetch both Timetable and Homework data."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 HA-Integration",
        "Content-Type": "application/x-www-form-urlencoded"
    })
    
    try:
        # 1. Login
        login_resp = session.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=10
        )
        login_resp.raise_for_status()
        login_json = login_resp.json()

        # FIXED: Safety check to prevent 'list' object has no attribute 'get'
        if not isinstance(login_json, dict):
            _LOGGER.error("Login failed: Expected dict but got %s: %s", type(login_json), login_json)
            return None

        token = login_json.get("meta", {}).get("session_id")

        if not token:
            _LOGGER.error("Login failed: No
