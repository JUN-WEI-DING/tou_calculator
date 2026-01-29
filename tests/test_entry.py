import json
from datetime import date, datetime, time

import pandas as pd

import tou_calculator as tou
from tou_calculator.calendar import TaiwanCalendar
from tou_calculator.errors import InvalidUsageInput, PowerKitError, TariffError
from tou_calculator.tariff import (
    DaySchedule,
    PeriodType,
    SeasonType,
    TaiwanDayTypeStrategy,
    TaiwanSeasonStrategy,
    TariffPlan,
    TariffProfile,
    TariffRate,
    TimeSlot,
    get_period,
)


class FixedCalendar:
    def is_holiday(self, target: object) -> object:
        if isinstance(target, pd.DatetimeIndex):
            return pd.Series(False, index=target)
        return False


def _build_profile() -> TariffProfile:
    schedule = DaySchedule(
        slots=[
            TimeSlot(
                start=time(0, 0), end=time(12, 0), period_type=PeriodType.OFF_PEAK
            ),
            TimeSlot(start=time(12, 0), end=time(18, 0), period_type=PeriodType.PEAK),
            TimeSlot(
                start=time(18, 0), end=time(0, 0), period_type=PeriodType.OFF_PEAK
            ),
        ]
    )
    schedules = {
        (season, day_type): schedule
        for season in SeasonType
        for day_type in ("weekday", "saturday", "sunday_holiday")
    }
    return TariffProfile(
        name="Test",
        season_strategy=TaiwanSeasonStrategy((6, 1), (9, 30)),
        day_type_strategy=TaiwanDayTypeStrategy(FixedCalendar()),
        schedules=schedules,
    )


def test_entry_calendar_and_tariffs(tmp_path) -> None:
    data = [
        {
            "date": "20240101",
            "description": "New Year",
            "isHoliday": True,
        }
    ]
    cache_file = tmp_path / "2024.json"
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    calendar = TaiwanCalendar(cache_dir=tmp_path)
    assert calendar.is_holiday(date(2024, 1, 1))
    assert tou.is_holiday(date(2024, 1, 1), calendar=calendar)

    helper_calendar = tou.taiwan_calendar(cache_dir=tmp_path)
    assert helper_calendar.is_holiday(date(2024, 1, 1))

    helper_plan = tou.residential_simple_2_tier_plan(calendar)
    assert isinstance(helper_plan, TariffPlan)

    named_plan = tou.plan("residential_simple_2_tier", calendar_instance=calendar)
    assert isinstance(named_plan, TariffPlan)


def test_entry_get_period_and_calculate_costs() -> None:
    profile = _build_profile()
    rate = TariffRate(
        period_costs={
            (SeasonType.SUMMER, PeriodType.OFF_PEAK): 1.0,
            (SeasonType.SUMMER, PeriodType.PEAK): 3.0,
        }
    )
    plan = TariffPlan(profile, rate)

    assert get_period(datetime(2024, 7, 1, 13, 0), profile) == PeriodType.PEAK
    assert tou.get_period(datetime(2024, 7, 1, 13, 0), profile) == PeriodType.PEAK

    usage = pd.Series(
        [1.5, 2.0],
        index=pd.DatetimeIndex(["2024-07-01 11:00", "2024-07-01 13:00"]),
    )
    costs = plan.calculate_costs(usage)
    assert list(costs.values) == [7.5]
    assert list(tou.calculate_costs(usage, plan).values) == [7.5]


def test_entry_named_helpers(tmp_path) -> None:
    cache_file = tmp_path / "2025.json"
    cache_file.write_text("[]", encoding="utf-8")

    assert "high_voltage_2_tier" in tou.available_plans()
    assert len(tou.available_plans()) > 0  # Bilingual names
    assert tou.period_at(
        datetime(2025, 7, 15, 10, 0),
        "residential_simple_2_tier",
        cache_dir=tmp_path,
    ) in {PeriodType.PEAK, PeriodType.OFF_PEAK, PeriodType.SEMI_PEAK}

    usage = pd.Series(
        [1.0, 2.0],
        index=pd.to_datetime(["2025-07-15 09:00", "2025-07-15 10:00"]),
    )
    costs = tou.costs(usage, "high_voltage_2_tier", cache_dir=tmp_path)
    assert (costs >= 0).all()


def test_errors_exports() -> None:
    assert issubclass(InvalidUsageInput, PowerKitError)
    assert issubclass(TariffError, PowerKitError)
