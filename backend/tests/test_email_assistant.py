# tests/test_email_assistant.py
#
# V0.7.1 (Fase 4b, Tarea 3.4): tests unitarios del patron AMD GAIA aplicado
# al Email Assistant.
#
#   - Deteccion heuristica de reuniones (sin LLM, 0 coste)
#   - Dataclass MeetingDetection (frozen, tipada)
#   - Funcion pura detect_calendar_conflicts() con half-open intervals
#
# Ejecutar:  cd backend && python -m pytest tests/test_email_assistant.py -v

import dataclasses
from datetime import datetime

import pytest

from app.tools.email_tool import (
    MeetingDetection,
    _heuristic_meeting_detection,
)
from app.api.endpoints.email_assistant import detect_calendar_conflicts


# ----------------------------------------------------------------------
# Helpers de test
# ----------------------------------------------------------------------

class _Block:
    """Imita un CalendarAvailability para los tests (status/date/hour_start/hour_end)."""

    def __init__(self, day: datetime, hour_start: int, hour_end: int, status: str = "busy"):
        self.date = datetime(day.year, day.month, day.day)
        self.hour_start = hour_start
        self.hour_end = hour_end
        self.status = status


_DAY = datetime(2026, 7, 3)  # un viernes cualquiera


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(_DAY.year, _DAY.month, _DAY.day, hour, minute)


# ----------------------------------------------------------------------
# Heuristica de deteccion de reuniones
# ----------------------------------------------------------------------

def test_heuristic_detection_high_confidence():
    d = _heuristic_meeting_detection("Let's meet", "Are you free next tuesday at 10am?")
    assert d.is_meeting_request is True
    assert d.confidence == "high"
    assert d.method == "heuristic"
    assert d.signals  # al menos una senal


def test_heuristic_detection_none():
    d = _heuristic_meeting_detection("Docs", "please check the docs when you can")
    assert d.is_meeting_request is False
    assert d.confidence == "none"
    assert d.signals == []


def test_heuristic_detection_keyword_plus_date_is_high():
    # Palabra de reunion ('vernos') + fecha/hora -> alta confianza.
    d = _heuristic_meeting_detection("Cita", "podemos vernos el martes a las 11:30")
    assert d.is_meeting_request is True
    assert d.confidence == "high"
    assert d.datetime_iso is not None


def test_heuristic_detection_date_only_is_low():
    # Solo fecha, sin palabra de reunion clara -> ambiguo, decide el LLM.
    d = _heuristic_meeting_detection("Info", "te lo mando el martes")
    assert d.is_meeting_request is False
    assert d.confidence == "low"


def test_heuristic_extracts_explicit_hour():
    # BUG Fase 4b: la hora explicita ('a las 11h') debe respetarse, no 10:00.
    d = _heuristic_meeting_detection(
        "reunion importante mañana",
        "reunion importante manana 2 de julio a las 11h",
    )
    assert d.is_meeting_request is True
    assert d.datetime_iso is not None
    assert d.datetime_iso.endswith("T11:00:00")


# ----------------------------------------------------------------------
# Dataclass MeetingDetection
# ----------------------------------------------------------------------

def test_meeting_detection_dataclass_is_frozen():
    d = MeetingDetection(
        is_meeting_request=True,
        confidence="high",
        signals=["let's meet"],
        reason="test",
    )
    assert dataclasses.is_dataclass(d)
    # frozen: no se puede reasignar un campo
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.is_meeting_request = False


def test_meeting_detection_dataclass_fields():
    d = MeetingDetection(
        is_meeting_request=False,
        confidence="none",
        signals=[],
        reason="sin senales",
    )
    # Campos con defaults
    assert d.datetime_iso is None
    assert d.method == "none"
    # Serializable a dict para respuesta HTTP
    as_dict = dataclasses.asdict(d)
    assert set(as_dict) == {
        "is_meeting_request",
        "confidence",
        "signals",
        "reason",
        "datetime_iso",
        "method",
    }


# ----------------------------------------------------------------------
# detect_calendar_conflicts() — half-open intervals [start, end)
# ----------------------------------------------------------------------

def test_detect_calendar_conflicts_halfopen_backtoback():
    # Reunion 10:00-11:00 frente a bloque 11:00-12:00 -> back-to-back, NO conflicto.
    block = _Block(_DAY, 11, 12)
    assert detect_calendar_conflicts(_at(10), _at(11), [block]) is False


def test_detect_calendar_conflicts_overlap():
    # Reunion 10:30-11:30 frente a bloque 10:00-11:00 -> solapamiento, SI conflicto.
    block = _Block(_DAY, 10, 11)
    assert detect_calendar_conflicts(_at(10, 30), _at(11, 30), [block]) is True


def test_detect_calendar_conflicts_exact():
    # Reunion 10:00-11:00 frente a bloque 10:00-11:00 -> mismo intervalo, SI conflicto.
    block = _Block(_DAY, 10, 11)
    assert detect_calendar_conflicts(_at(10), _at(11), [block]) is True


def test_detect_calendar_conflicts_ignores_free_blocks():
    # Un bloque no busy/unavailable no genera conflicto.
    block = _Block(_DAY, 10, 11, status="available")
    assert detect_calendar_conflicts(_at(10), _at(11), [block]) is False


def test_detect_calendar_conflicts_google_events():
    # Evento de Google Calendar 10:00-11:00, propuesta 10:30-11:30 -> conflicto.
    gcal = [{"start": _at(10).isoformat(), "end": _at(11).isoformat()}]
    assert detect_calendar_conflicts(_at(10, 30), _at(11, 30), [], gcal) is True


def test_detect_calendar_conflicts_google_events_backtoback():
    # Evento GCal 09:00-10:00, propuesta 10:00-11:00 -> back-to-back, NO conflicto.
    gcal = [{"start": _at(9).isoformat(), "end": _at(10).isoformat()}]
    assert detect_calendar_conflicts(_at(10), _at(11), [], gcal) is False


def test_detect_calendar_conflicts_none_when_empty():
    assert detect_calendar_conflicts(_at(10), _at(11), [], []) is False
