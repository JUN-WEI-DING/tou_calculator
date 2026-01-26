"""Taiwan holiday calendar with API-backed data and local caching."""

from __future__ import annotations

import json
import time
from datetime import date, datetime
from functools import singledispatchmethod
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from platformdirs import user_cache_path

try:
    import pandas as pd
except ImportError:
    pd = None

from tou_calculator.errors import CalendarError

HOLIDAY_API_URL = (
    "https://raw.githubusercontent.com/ruyut/TaiwanCalendar/master/data/{year}.json"
)


class _HolidayCache:
    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._memory: dict[int, set[date]] = {}
        self._ensure_cache_dir()

    @property
    def memory(self) -> dict[int, set[date]]:
        return self._memory

    def _ensure_cache_dir(self) -> None:
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            fallback_dir = (
                Path.cwd() / ".cache" / "tou_calculator" / "calendar" / "taiwan"
            )
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self._cache_dir = fallback_dir

    def read_file(self, year: int) -> list[dict[str, Any]] | None:
        cache_file = self._cache_dir / f"{year}.json"
        if not cache_file.exists():
            return None
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)

    def write_file(self, year: int, data: list[dict[str, Any]]) -> None:
        cache_file = self._cache_dir / f"{year}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class _HolidayParser:
    def extract_holidays(self, data: list[dict[str, Any]]) -> set[date]:
        holidays = set()
        for entry in data:
            if entry.get("isHoliday", False):
                date_str = entry.get("date", "")
                description = entry.get("description", "")
                if len(date_str) == 8:
                    try:
                        d = date(
                            int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
                        )
                        if d.weekday() == 5 and not description:
                            continue
                        holidays.add(d)
                    except ValueError:
                        continue
        return holidays

    def static_holidays(self, year: int) -> set[date]:
        holidays = set()

        current = date(year, 1, 1)
        end = date(year, 12, 31)
        while current <= end:
            if current.weekday() == 6:
                holidays.add(current)
            current = date.fromordinal(current.toordinal() + 1)

        static_holidays = [
            (1, 1),
            (2, 28),
            (4, 4),
            (5, 1),
            (9, 28),
            (10, 10),
            (10, 25),
            (12, 25),
        ]
        for month, day in static_holidays:
            holidays.add(date(year, month, day))

        return holidays


class _HolidayFetcher:
    def __init__(self, api_timeout: int) -> None:
        self._api_timeout = api_timeout

    def fetch(self, year: int) -> list[dict[str, Any]]:
        url = HOLIDAY_API_URL.format(year=year)
        last_exc: Exception | None = None
        delay = 1.0
        for attempt in range(3):
            try:
                with urlopen(url, timeout=self._api_timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except (URLError, TimeoutError, OSError) as exc:
                last_exc = exc
                if attempt == 2:
                    break
                time.sleep(min(delay, 10.0))
                delay *= 2
        if last_exc is not None:
            raise last_exc
        raise CalendarError("Holiday API fetch failed")


class _HolidayLoader:
    def __init__(self, cache_dir: Path, api_timeout: int = 10) -> None:
        self._cache = _HolidayCache(cache_dir)
        self._fetcher = _HolidayFetcher(api_timeout)
        self._parser = _HolidayParser()
        self._holiday_cache = self._cache.memory

    def load_holidays(self, year: int) -> set[date]:
        if year in self._holiday_cache:
            return self._holiday_cache[year]

        try:
            data = self._cache.read_file(year)
            if data is not None:
                holidays = self._parser.extract_holidays(data)
                self._holiday_cache[year] = holidays
                return holidays
        except Exception:
            pass

        try:
            data = self._fetcher.fetch(year)
            self._cache.write_file(year, data)
            holidays = self._parser.extract_holidays(data)
            self._holiday_cache[year] = holidays
            return holidays
        except Exception:
            pass

        holidays = self._parser.static_holidays(year)
        self._holiday_cache[year] = holidays
        return holidays


class TaiwanCalendar:
    """Taiwan calendar with holiday rules."""

    def __init__(self, cache_dir: Path | None = None, api_timeout: int = 10) -> None:
        cache_dir = Path(cache_dir) if cache_dir else user_cache_path("tou_calculator")
        cache_dir = cache_dir / "calendar" / "taiwan"
        self._loader = _HolidayLoader(cache_dir, api_timeout)

    @singledispatchmethod
    def is_holiday(self, target: object) -> bool | pd.Series:
        raise CalendarError(f"Unsupported type: {type(target)}")

    @is_holiday.register
    def _(self, target: date) -> bool:
        if target.weekday() == 6:
            return True
        holidays = self._loader.load_holidays(target.year)
        return target in holidays

    @is_holiday.register
    def _(self, target: datetime) -> bool:
        return self.is_holiday(target.date())

    if pd is not None:

        @is_holiday.register
        def _(self, target: pd.DatetimeIndex) -> pd.Series:
            is_sunday = target.dayofweek == 6

            unique_years = target.year.unique()
            all_holidays = set()
            for year in unique_years:
                all_holidays.update(self._loader.load_holidays(int(year)))

            target_normalized = target.normalize()

            if not all_holidays:
                return pd.Series(is_sunday, index=target, name="is_holiday")

            holiday_ts = pd.DatetimeIndex(list(all_holidays))
            is_in_holidays = target_normalized.isin(holiday_ts)

            final_mask = is_sunday | is_in_holidays
            return pd.Series(final_mask, index=target, name="is_holiday")


def taiwan_calendar(
    cache_dir: Path | None = None, api_timeout: int = 10
) -> TaiwanCalendar:
    return TaiwanCalendar(cache_dir=cache_dir, api_timeout=api_timeout)
