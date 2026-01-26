import json
from datetime import date

from tou_calculator.calendar import TaiwanCalendar


def test_taiwan_calendar_weekend_rules(tmp_path) -> None:
    cache_file = tmp_path / "2025.json"
    cache_file.write_text("[]", encoding="utf-8")

    cal = TaiwanCalendar(cache_dir=tmp_path)
    assert cal.is_holiday(date(2025, 7, 12)) is False
    assert cal.is_holiday(date(2025, 7, 13)) is True


def test_taiwan_calendar_cached_holiday(tmp_path) -> None:
    data = [
        {
            "date": "20251010",
            "description": "National Day",
            "isHoliday": True,
        }
    ]
    cache_file = tmp_path / "2025.json"
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    cal = TaiwanCalendar(cache_dir=tmp_path)
    assert cal.is_holiday(date(2025, 10, 10)) is True
