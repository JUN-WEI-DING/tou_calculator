import json
from datetime import date
from unittest.mock import patch

import pytest

from tou_calculator.calendar import TaiwanCalendar


@pytest.fixture
def offline_calendar(tmp_path):
    """
    Returns a TaiwanCalendar instance that is forced offline.
    Prevents network calls during testing.
    """
    with patch(
        "tou_calculator.calendar._HolidayFetcher.fetch",
        side_effect=RuntimeError("Offline mode"),
    ):
        yield TaiwanCalendar(cache_dir=tmp_path)


def test_taiwan_calendar_weekend_rules(offline_calendar) -> None:
    # Saturday is not a holiday by default if not in list
    assert offline_calendar.is_holiday(date(2025, 7, 12)) is False
    # Sunday is always a holiday
    assert offline_calendar.is_holiday(date(2025, 7, 13)) is True


def test_taiwan_calendar_cached_holiday(tmp_path) -> None:
    data = [
        {
            "date": "20251010",
            "description": "National Day",
            "isHoliday": True,
        }
    ]

    # Write cache file directly
    cache_file = tmp_path / "2025.json"
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    cal = TaiwanCalendar(cache_dir=tmp_path)
    assert cal.is_holiday(date(2025, 10, 10)) is True
