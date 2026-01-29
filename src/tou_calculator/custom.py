"""Helpers for building custom calendars and tariff definitions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, time
from functools import singledispatchmethod
from typing import Any

try:
    import pandas as pd
except ImportError:
    pd = None

from tou_calculator.errors import CalendarError, TariffError
from tou_calculator.models import (
    BillingCycleType,
    ConsumptionTier,
    DaySchedule,
    PeriodType,
    SeasonType,
    TariffRate,
    TimeSlot,
    _label_value,
)
from tou_calculator.tariff import (
    DayTypeStrategy,
    SeasonStrategy,
    TariffPlan,
    TariffProfile,
)


class CustomCalendar:
    """Calendar based on explicit holidays and optional weekend rules."""

    def __init__(
        self,
        holidays: Iterable[date] | None = None,
        weekend_days: Iterable[int] | None = None,
    ) -> None:
        self._holidays = set(holidays or [])
        self._weekend_days = set(weekend_days or [])

    @singledispatchmethod
    def is_holiday(self, target: object) -> Any:
        raise CalendarError(f"Unsupported type: {type(target)}")

    @is_holiday.register
    def _(self, target: date) -> bool:
        return target in self._holidays or target.weekday() in self._weekend_days

    @is_holiday.register
    def _(self, target: datetime) -> bool:
        return self.is_holiday(target.date())

    if pd is not None:

        @is_holiday.register
        def _(self, target: pd.DatetimeIndex) -> pd.Series:
            is_weekend = target.dayofweek.isin(sorted(self._weekend_days))
            if not self._holidays:
                return pd.Series(is_weekend, index=target, name="is_holiday")

            holiday_ts = pd.DatetimeIndex(list(self._holidays))
            is_holiday = target.normalize().isin(holiday_ts)
            return pd.Series(is_weekend | is_holiday, index=target, name="is_holiday")


def custom_calendar(
    holidays: Iterable[date] | None = None,
    weekend_days: Iterable[int] | None = None,
) -> CustomCalendar:
    return CustomCalendar(holidays=holidays, weekend_days=weekend_days)


class WeekdayDayTypeStrategy:
    """Map weekday numbers to day type labels with optional holiday override."""

    def __init__(
        self,
        calendar: Any,
        weekday_map: Mapping[int, str] | None = None,
        holiday_label: str = "holiday",
    ) -> None:
        self._calendar = calendar
        self._weekday_map = weekday_map or {
            0: "weekday",
            1: "weekday",
            2: "weekday",
            3: "weekday",
            4: "weekday",
            5: "saturday",
            6: "sunday",
        }
        self._holiday_label = holiday_label

    def get_day_type(self, target: date) -> str:
        if self._calendar.is_holiday(target):
            return self._holiday_label
        return self._weekday_map.get(target.weekday(), "weekday")

    def get_all_day_types(self) -> list[str]:
        seen = list(dict.fromkeys(self._weekday_map.values()))
        if self._holiday_label not in seen:
            seen.append(self._holiday_label)
        return seen


def build_day_schedule(slots: Sequence[TimeSlot | Mapping[str, Any]]) -> DaySchedule:
    return DaySchedule(slots=[_build_slot(slot) for slot in slots])


def build_tariff_profile(
    name: str,
    season_strategy: SeasonStrategy,
    day_type_strategy: DayTypeStrategy,
    schedules: Mapping[
        tuple[Any, Any], DaySchedule | Sequence[TimeSlot | Mapping[str, Any]]
    ]
    | Sequence[Mapping[str, Any]],
    default_period: PeriodType | str = PeriodType.OFF_PEAK,
) -> TariffProfile:
    schedule_map: dict[tuple[Any, Any], DaySchedule] = {}

    if isinstance(schedules, Mapping):
        for (season, day_type), schedule in schedules.items():
            schedule_map[
                (
                    _resolve_season(season, season_strategy),
                    _resolve_day_type(day_type, day_type_strategy),
                )
            ] = _ensure_schedule(schedule)
    else:
        for item in schedules:
            season = _resolve_season(item["season"], season_strategy)
            day_type = _resolve_day_type(item["day_type"], day_type_strategy)
            schedule_map[(season, day_type)] = build_day_schedule(item["slots"])

    return TariffProfile(
        name=name,
        season_strategy=season_strategy,
        day_type_strategy=day_type_strategy,
        schedules=schedule_map,
        default_period=default_period,
    )


def build_tariff_rate(
    period_costs: Mapping[tuple[Any, Any], float]
    | Sequence[Mapping[str, Any]]
    | None = None,
    tiered_rates: Sequence[ConsumptionTier | Mapping[str, Any]] | None = None,
    season_strategy: SeasonStrategy | None = None,
) -> TariffRate:
    period_cost_map: dict[tuple[Any, Any], float] = {}
    if period_costs:
        if isinstance(period_costs, Mapping):
            for (season, period), cost in period_costs.items():
                period_cost_map[
                    (_resolve_season(season, season_strategy), _resolve_period(period))
                ] = float(cost)
        else:
            for item in period_costs:
                season = _resolve_season(item["season"], season_strategy)
                period = _resolve_period(item["period"])
                period_cost_map[(season, period)] = float(item["cost"])

    tiers: list[ConsumptionTier] = []
    if tiered_rates:
        for t_item in tiered_rates:
            if isinstance(t_item, ConsumptionTier):
                tiers.append(t_item)
            else:
                tiers.append(
                    ConsumptionTier(
                        start_kwh=float(t_item["start_kwh"]),
                        end_kwh=float(t_item["end_kwh"]),
                        summer_cost=float(t_item["summer_cost"]),
                        non_summer_cost=float(t_item["non_summer_cost"]),
                    )
                )

    return TariffRate(period_costs=period_cost_map, tiered_rates=tiers)


def build_tariff_plan(
    profile: TariffProfile,
    rates: TariffRate,
    billing_cycle_type: BillingCycleType = BillingCycleType.MONTHLY,
) -> TariffPlan:
    return TariffPlan(profile, rates, billing_cycle_type)


def _build_slot(slot: TimeSlot | Mapping[str, Any]) -> TimeSlot:
    if isinstance(slot, TimeSlot):
        return slot
    start = _parse_time(slot["start"])
    end = _parse_time(slot["end"])
    period = _resolve_period(slot["period"])
    return TimeSlot(start=start, end=end, period_type=period)


def _parse_time(value: time | str) -> time:
    if isinstance(value, time):
        return value
    if not isinstance(value, str):
        raise TariffError(f"Unsupported time format: {value!r}")
    try:
        hour_str, minute_str = value.split(":")
        hour = int(hour_str)
        minute = int(minute_str)
    except (ValueError, AttributeError) as exc:
        raise TariffError(f"Invalid time format: {value}") from exc
    if hour == 24 and minute == 0:
        return time(0, 0)
    try:
        return time(hour, minute)
    except ValueError as exc:
        raise TariffError(f"Invalid time value: {value}") from exc


def _resolve_period(period: PeriodType | str) -> PeriodType | str:
    if isinstance(period, PeriodType):
        return period
    if isinstance(period, str):
        try:
            return PeriodType(period)
        except ValueError:
            return period
    return _label_value(period)


def _resolve_season(
    season: SeasonType | str, season_strategy: SeasonStrategy | None
) -> Any:
    if isinstance(season, SeasonType):
        return season
    if isinstance(season, str):
        try:
            return SeasonType(season)
        except ValueError:
            pass
    if season_strategy is None:
        return season
    for candidate in season_strategy.get_all_seasons():
        if candidate == season or _label_value(candidate) == _label_value(season):
            return candidate
    return season


def _resolve_day_type(day_type: Any, day_type_strategy: DayTypeStrategy | None) -> Any:
    if day_type_strategy is None:
        return day_type
    for candidate in day_type_strategy.get_all_day_types():
        if candidate == day_type or str(candidate) == str(day_type):
            return candidate
    return day_type


def _ensure_schedule(
    schedule: DaySchedule | Sequence[TimeSlot | Mapping[str, Any]],
) -> DaySchedule:
    if isinstance(schedule, DaySchedule):
        return schedule
    return build_day_schedule(schedule)
