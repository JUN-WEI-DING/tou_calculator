"""Taiwan holiday calendar with API-backed data and local caching."""

from __future__ import annotations

import json
import time
from datetime import date, datetime
from functools import singledispatchmethod
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from platformdirs import user_cache_path

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from zhdate import ZhDate

    LUNAR_AVAILABLE = True
except ImportError:
    LUNAR_AVAILABLE = False

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

    def _lunar_to_solar(self, year: int, month: int, day: int) -> date | None:
        """Convert lunar date to solar date."""
        if not LUNAR_AVAILABLE:
            return None
        try:
            zh_date = ZhDate(year, month, day)
            return zh_date.to_datetime().date()
        except Exception:
            return None

    def lunar_holidays(self, year: int) -> set[date]:
        """Calculate Taiwan national holidays using lunar calendar.

        According to Taipower regulations:
        - Spring Festival (Lunar 1/1-3/0, adjusted if falls on Sat/Sun)
        - Tomb Sweeping Day (Solar 4/4, already in static)
        - Dragon Boat Festival (Lunar 5/5)
        - Mid-Autumn Festival (Lunar 8/15)

        This optimized version uses efficient Sunday calculation.
        """

        holidays = set()

        # All Sundays - calculate directly without iteration
        # Find first Sunday of the year, then add 7 days each time
        jan_1 = date(year, 1, 1)
        first_sunday_offset = (6 - jan_1.weekday()) % 7  # 6 = Sunday
        first_sunday = date.fromordinal(jan_1.toordinal() + first_sunday_offset)

        # Add all Sundays (52 or 53 per year)
        current = first_sunday
        while current.year == year:
            holidays.add(current)
            current = date.fromordinal(current.toordinal() + 7)

        # Fixed solar holidays
        fixed_solar = [
            (1, 1),  # New Year's Day
            (2, 28),  # Peace Memorial Day
            (4, 4),  # Tomb Sweeping Day (Children's Day)
            (5, 1),  # Labor Day
            (10, 10),  # National Day
        ]
        for month, day in fixed_solar:
            holidays.add(date(year, month, day))

        # Lunar holidays
        # Spring Festival: Lunar 1/1-1/3 (3 consecutive days)
        for day in range(1, 4):
            solar_date = self._lunar_to_solar(year, 1, day)
            if solar_date and solar_date.year == year:
                holidays.add(solar_date)

        # Dragon Boat Festival: Lunar 5/5
        dragon_boat = self._lunar_to_solar(year, 5, 5)
        if dragon_boat and dragon_boat.year == year:
            holidays.add(dragon_boat)

        # Mid-Autumn Festival: Lunar 8/15
        mid_autumn = self._lunar_to_solar(year, 8, 15)
        if mid_autumn and mid_autumn.year == year:
            holidays.add(mid_autumn)

        return holidays

    def static_holidays(self, year: int) -> set[date]:
        """Fallback static holidays when API and lunar calculation fail."""
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
            except HTTPError as exc:
                # 404 means year doesn't exist yet - don't retry
                if exc.code == 404:
                    raise exc
                last_exc = exc
                if attempt == 2:
                    break
                time.sleep(min(delay, 10.0))
                delay *= 2
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

        # Try local cache first
        try:
            data = self._cache.read_file(year)
            if data is not None:
                holidays = self._parser.extract_holidays(data)
                self._holiday_cache[year] = holidays
                return holidays
        except Exception:
            pass

        # Try API fetch - skip for far future years to avoid timeout delays
        # API only has current and recent past years
        current_year = date.today().year
        try_api = year <= current_year + 1

        if try_api:
            try:
                data = self._fetcher.fetch(year)
                self._cache.write_file(year, data)
                holidays = self._parser.extract_holidays(data)
                self._holiday_cache[year] = holidays
                return holidays
            except HTTPError as exc:
                # 404 means year doesn't exist - fall through to lunar
                if exc.code != 404:
                    raise
            except Exception:
                pass

        # Fallback: lunar calendar calculation
        holidays = self._parser.lunar_holidays(year)
        self._holiday_cache[year] = holidays
        return holidays


class TaiwanCalendar:
    """Taiwan calendar with holiday rules."""

    def __init__(self, cache_dir: Path | None = None, api_timeout: int = 10) -> None:
        cache_dir = Path(cache_dir) if cache_dir else user_cache_path("tou_calculator")
        cache_dir = cache_dir / "calendar" / "taiwan"
        self._loader = _HolidayLoader(cache_dir, api_timeout)

    def preload_years(self, years: set[int]) -> None:
        """Preload holiday data for multiple years in batch.

        This method loads all holiday data for the specified years into memory
        in a single operation, significantly improving performance for bulk
        operations like evaluating large time series.

        Args:
            years: Set of years to preload (e.g., {2024, 2025})
        """
        for year in years:
            self._loader.load_holidays(year)

    @singledispatchmethod
    def is_holiday(self, target: object) -> Any:
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
