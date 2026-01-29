"""Taiwan time-of-use tariff definitions and calculation engine."""

from __future__ import annotations

import functools
from datetime import date, datetime, time
from typing import Any, Protocol

try:
    import numpy as np
    import numpy.typing as npt
    import pandas as pd
except ImportError:
    np: Any = None  # type: ignore
    npt: Any = None  # type: ignore
    pd: Any = None  # type: ignore

from tou_calculator.errors import InvalidUsageInput, TariffError
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


class SeasonStrategy(Protocol):
    def get_season(self, target: date) -> SeasonType | str: ...

    def get_all_seasons(self) -> list[SeasonType | str]: ...


class DayTypeStrategy(Protocol):
    def get_day_type(self, target: date) -> str: ...

    def get_all_day_types(self) -> list[str]: ...


class TaiwanSeasonStrategy:
    def __init__(
        self, summer_start: tuple[int, int], summer_end: tuple[int, int]
    ) -> None:
        self._start = summer_start
        self._end = summer_end

    def get_season(self, target: date) -> SeasonType:
        current = (target.month, target.day)
        start = self._start
        end = self._end
        if start <= end:
            return (
                SeasonType.SUMMER if start <= current <= end else SeasonType.NON_SUMMER
            )
        return (
            SeasonType.SUMMER
            if current >= start or current <= end
            else SeasonType.NON_SUMMER
        )

    def get_all_seasons(self) -> list[SeasonType | str]:
        return [SeasonType.SUMMER, SeasonType.NON_SUMMER]


class TaiwanDayTypeStrategy:
    def __init__(self, calendar: Any) -> None:
        self._calendar = calendar

    def get_day_type(self, target: date) -> str:
        if self._calendar.is_holiday(target):
            return "sunday_holiday"
        if target.weekday() == 5:
            return "saturday"
        return "weekday"

    def get_day_types_batch(self, dates: pd.Series) -> dict[date, str]:
        """Batch get day types for multiple dates using vectorized calendar lookup.

        This method is significantly faster than calling get_day_type() repeatedly
        for large numbers of dates.

        Args:
            dates: pandas Series with date objects

        Returns:
            Dictionary mapping each date to its day type
        """
        # Create DatetimeIndex for vectorized lookup
        dates_index = pd.DatetimeIndex(dates.values)
        is_saturday = dates_index.dayofweek == 5

        # Use vectorized is_holiday if available (for DatetimeIndex)
        is_holiday_series = self._calendar.is_holiday(dates_index)

        day_types = {}
        for dt, is_sat, is_hol in zip(dates, is_saturday, is_holiday_series):
            if is_hol:
                day_types[dt] = "sunday_holiday"
            elif is_sat:
                day_types[dt] = "saturday"
            else:
                day_types[dt] = "weekday"
        return day_types

    def get_all_day_types(self) -> list[str]:
        return ["weekday", "saturday", "sunday_holiday"]


class TariffProfile:
    def __init__(
        self,
        name: str,
        season_strategy: SeasonStrategy,
        day_type_strategy: DayTypeStrategy,
        schedules: dict[tuple[Any, Any], DaySchedule],
        default_period: PeriodType | str = PeriodType.OFF_PEAK,
    ) -> None:
        self.name = name
        self.season_strategy = season_strategy
        self.day_type_strategy = day_type_strategy
        self.schedules = schedules
        self.default_period = default_period
        self._engine: _TariffEngine | None = None

    @property
    def engine(self) -> _TariffEngine:
        if self._engine is None:
            self._engine = _TariffEngine(self)
        return self._engine

    def evaluate(self, index: pd.DatetimeIndex) -> pd.DataFrame:
        if pd is None:
            raise TariffError("pandas is required for tariff evaluation")
        return self.engine.evaluate(index)

    def describe(self) -> dict[str, Any]:
        def _slot_to_dict(slot: TimeSlot) -> dict[str, str]:
            return {
                "start": slot.start.strftime("%H:%M"),
                "end": slot.end.strftime("%H:%M"),
                "period": _label_value(slot.period_type),
            }

        def _schedule_key(item: tuple[tuple[Any, Any], DaySchedule]) -> tuple[str, str]:
            (season, day_type), _ = item
            season_key = season.value if isinstance(season, SeasonType) else str(season)
            return (season_key, str(day_type))

        schedules = []
        for (season, day_type), schedule in sorted(
            self.schedules.items(), key=_schedule_key
        ):
            schedules.append(
                {
                    "season": _label_value(season),
                    "day_type": str(day_type),
                    "slots": [_slot_to_dict(slot) for slot in schedule.slots],
                }
            )

        seasons = [
            _label_value(season) for season in self.season_strategy.get_all_seasons()
        ]
        day_types = [
            str(day_type) for day_type in self.day_type_strategy.get_all_day_types()
        ]

        return {
            "name": self.name,
            "seasons": seasons,
            "day_types": day_types,
            "schedules": schedules,
        }


class _TariffEngine:
    def __init__(self, profile: TariffProfile) -> None:
        self.profile = profile
        if np is not None:
            self._build_lookup_table()

    def _build_lookup_table(self) -> None:
        self.seasons = self.profile.season_strategy.get_all_seasons()
        self.day_types = self.profile.day_type_strategy.get_all_day_types()

        self._season_map = {s: i for i, s in enumerate(self.seasons)}
        self._day_type_map = {dt: i for i, dt in enumerate(self.day_types)}

        self._period_types = [self.profile.default_period]
        seen = {self.profile.default_period}
        for schedule in self.profile.schedules.values():
            for slot in schedule.slots:
                if slot.period_type not in seen:
                    self._period_types.append(slot.period_type)
                    seen.add(slot.period_type)

        self._period_map_rev = {pt: i for i, pt in enumerate(self._period_types)}

        shape = (len(self.seasons), len(self.day_types), 1440)
        self._lookup_table: npt.NDArray[np.int8] = np.zeros(shape, dtype=np.int8)

        for (season, day_type), schedule in self.profile.schedules.items():
            s_idx = self._season_map.get(season)
            d_idx = self._day_type_map.get(day_type)
            if s_idx is None or d_idx is None:
                continue

            for slot in schedule.slots:
                p_idx = self._period_map_rev[slot.period_type]
                start_min = slot.start.hour * 60 + slot.start.minute
                end_min = slot.end.hour * 60 + slot.end.minute

                if start_min < end_min:
                    self._lookup_table[s_idx, d_idx, start_min:end_min] = p_idx
                else:
                    self._lookup_table[s_idx, d_idx, start_min:] = p_idx
                    self._lookup_table[s_idx, d_idx, :end_min] = p_idx

    def evaluate(self, index: pd.DatetimeIndex) -> pd.DataFrame:
        if pd is None or np is None:
            raise ImportError("pandas and numpy are required for vectorized lookup")
        if not isinstance(index, pd.DatetimeIndex):
            raise TypeError("Index must be a pandas.DatetimeIndex")

        # Preload all years for batch calendar optimization
        unique_years = index.year.unique()
        years_set = {int(y) for y in unique_years}
        self._preload_calendar_years(years_set)

        unique_dates = pd.Series(index.normalize().unique())

        # Season mapping (fast - no calendar needed)
        date_to_season = unique_dates.dt.date.apply(
            self.profile.season_strategy.get_season
        )
        season_map = dict(zip(unique_dates, date_to_season))
        season_objs = index.normalize().map(season_map)
        season_series = pd.Series(season_objs, index=index, name="season")
        season_codes = (
            season_objs.map(self._season_map).fillna(0).astype(np.int8).values
        )

        # Day type mapping - use batch method for vectorized calendar lookup
        day_type_strategy = self.profile.day_type_strategy
        if hasattr(day_type_strategy, "get_day_types_batch"):
            date_to_day_type = day_type_strategy.get_day_types_batch(unique_dates)
        else:
            date_to_day_type = {
                dt: day_type_strategy.get_day_type(dt) for dt in unique_dates.dt.date
            }
        day_type_map = date_to_day_type
        day_type_objs = index.normalize().map(day_type_map)
        day_type_series = pd.Series(day_type_objs, index=index, name="day_type")
        day_type_codes = (
            day_type_objs.map(self._day_type_map).fillna(0).astype(np.int8).values
        )

        minutes = index.hour * 60 + index.minute
        period_codes = self._lookup_table[season_codes, day_type_codes, minutes]
        period_objs = np.array(self._period_types)[period_codes]
        period_series = pd.Series(period_objs, index=index, name="period")

        return pd.concat([season_series, day_type_series, period_series], axis=1)

    def _preload_calendar_years(self, years: set[int]) -> None:
        """Preload calendar data for all years in batch for optimization."""
        day_type_strategy = self.profile.day_type_strategy
        if hasattr(day_type_strategy, "_calendar"):
            calendar = day_type_strategy._calendar
            if hasattr(calendar, "preload_years"):
                calendar.preload_years(years)

    def get_period_type_scalar(self, dt: datetime) -> PeriodType | str:
        season = self.profile.season_strategy.get_season(dt.date())
        day_type = self.profile.day_type_strategy.get_day_type(dt.date())
        schedule = self.profile.schedules.get((season, day_type))
        if not schedule:
            return self.profile.default_period
        return self._find_slot_type(dt.time(), schedule, self.profile.default_period)

    @staticmethod
    def _find_slot_type(
        t: time,
        schedule: DaySchedule,
        default_period: PeriodType | str,
    ) -> PeriodType | str:
        for slot in schedule.slots:
            if slot.start <= t < slot.end:
                return slot.period_type
            if slot.start > slot.end:
                if t >= slot.start or t < slot.end:
                    return slot.period_type
        return default_period


@functools.singledispatch
def get_period(target: object, profile: TariffProfile) -> PeriodType | str | pd.Series:
    raise NotImplementedError(f"Unsupported type: {type(target)}")


@get_period.register(datetime)
def _(target: datetime, profile: TariffProfile) -> PeriodType | str:
    return profile.engine.get_period_type_scalar(target)


if pd is not None:

    @get_period.register(pd.DatetimeIndex)
    def _(target: pd.DatetimeIndex, profile: TariffProfile) -> pd.Series:
        return profile.engine.evaluate(target)["period"]


@functools.singledispatch
def get_context(target: object, profile: TariffProfile) -> Any:
    raise NotImplementedError(f"Unsupported type: {type(target)}")


@get_context.register(datetime)
def _(target: datetime, profile: TariffProfile) -> dict[str, Any]:
    season = profile.season_strategy.get_season(target.date())
    day_type = profile.day_type_strategy.get_day_type(target.date())
    period = profile.engine.get_period_type_scalar(target)
    return {
        "season": season,
        "day_type": day_type,
        "period": period,
    }


if pd is not None:

    @get_context.register(pd.DatetimeIndex)
    def _(target: pd.DatetimeIndex, profile: TariffProfile) -> pd.DataFrame:
        return profile.engine.evaluate(target)


class TariffPlan:
    def __init__(
        self,
        profile: TariffProfile,
        rates: TariffRate,
        billing_cycle_type: BillingCycleType = BillingCycleType.MONTHLY,
    ) -> None:
        self.profile = profile
        self.rates = rates
        self.billing_cycle_type = billing_cycle_type

    @property
    def name(self) -> str:
        return self.profile.name

    def describe(self) -> dict[str, Any]:
        return {
            "profile": self.profile.describe(),
            "rates": self.rates.describe(),
        }

    def pricing_context(
        self,
        target: object,
        usage_kwh: float | pd.Series | None = None,
        include_details: bool = False,
    ) -> Any:
        if pd is None and hasattr(target, "__iter__"):
            raise TariffError("pandas is required for multi-point context evaluation")
        if usage_kwh is not None and self.rates.tiered_rates:
            raise InvalidUsageInput(
                "usage-based pricing is not supported for tiered plans; "
                "use calculate_costs for monthly billing totals."
            )

        if isinstance(target, datetime):
            context = get_context(target, self.profile)
            season = context["season"]
            period = context["period"]
            unit_cost: float | None = None
            cost: float | None = None

            if not self.rates.tiered_rates:
                unit_cost = self.rates.get_cost(season, period)
                if usage_kwh is not None:
                    cost = float(usage_kwh) * unit_cost

            result = {
                "season": _label_value(season),
                "period": _label_value(period),
                "rate": unit_cost,
                "cost": cost,
            }
            if include_details:
                return {
                    "context": result,
                    "rate_details": self.rates.describe(),
                    "profile_details": self.profile.describe(),
                }
            return result

        if pd is None or not isinstance(target, pd.DatetimeIndex):
            raise InvalidUsageInput("target must be a datetime or pandas.DatetimeIndex")

        context_df = self.profile.evaluate(target)
        seasons = context_df["season"]
        periods = context_df["period"]

        if self.rates.tiered_rates:
            rate_series = pd.Series([None] * len(target), index=target, name="rate")
            cost_series = pd.Series([None] * len(target), index=target, name="cost")
        else:
            rate_series = pd.Series(
                [
                    self.rates.get_cost(season, period)
                    for season, period in zip(seasons, periods)
                ],
                index=target,
                name="rate",
            )
            if usage_kwh is None:
                cost_series = pd.Series([None] * len(target), index=target, name="cost")
            else:
                if not isinstance(usage_kwh, pd.Series):
                    raise InvalidUsageInput("usage must be a pandas.Series")
                cost_series = (usage_kwh * rate_series).rename("cost")

        result = pd.DataFrame(
            {
                "season": seasons.apply(_label_value),
                "period": periods.apply(_label_value),
                "rate": rate_series,
                "cost": cost_series,
            },
            index=target,
        )

        if include_details:
            return {
                "context": result,
                "rate_details": self.rates.describe(),
                "profile_details": self.profile.describe(),
            }
        return result

    def calculate_costs(self, usage_kwh: pd.Series) -> pd.Series:
        if pd is None:
            raise TariffError("pandas is required for cost calculation")
        _validate_usage_series(usage_kwh)

        if self.rates.tiered_rates:
            return self._calculate_tiered_costs(usage_kwh)

        context = self.profile.evaluate(usage_kwh.index)
        unit_costs = pd.Series(
            [
                self.rates.get_cost(season, period)
                for season, period in zip(context["season"], context["period"])
            ],
            index=usage_kwh.index,
        )
        interval_costs = usage_kwh * unit_costs
        month_index = _month_group_index(usage_kwh.index)
        monthly_costs = interval_costs.groupby(month_index.to_period("M")).sum()
        monthly_costs.index = monthly_costs.index.to_timestamp()
        monthly_costs.name = "cost"
        return monthly_costs

    def _calculate_tiered_costs(self, usage_kwh: pd.Series) -> pd.Series:
        context = self.profile.evaluate(usage_kwh.index)
        billing_costs: dict[pd.Timestamp, float] = {}

        # Use billing period grouping instead of monthly grouping
        period_groups = usage_kwh.groupby(
            _billing_period_group_index(usage_kwh.index, self.billing_cycle_type)
        )

        sorted_tiers = sorted(self.rates.tiered_rates, key=lambda x: x.start_kwh)

        # For bimonthly billing, tier limits are doubled
        tier_multiplier = 2 if self.billing_cycle_type != BillingCycleType.MONTHLY else 1

        for period, period_usage in period_groups:
            total_usage_kwh = period_usage.sum()
            if total_usage_kwh == 0:
                billing_costs[period.to_timestamp()] = 0.0
                continue

            period_context = context.loc[period_usage.index]
            season = period_context["season"].mode().iloc[0]
            season_label = _label_value(season)

            total_cost = 0.0
            remaining_kwh = total_usage_kwh
            last_limit_kwh = 0.0

            for tier in sorted_tiers:
                if remaining_kwh <= 0:
                    break

                # Adjust tier limits for bimonthly billing
                tier_end = tier.end_kwh if tier.end_kwh < 999999 else float("inf")
                tier_start = last_limit_kwh
                tier_end = tier_end if tier_multiplier == 1 else tier_end * tier_multiplier

                # Calculate usage within this tier
                tier_limit_kwh = tier_end - tier_start

                usage_in_tier_kwh = min(remaining_kwh, tier_limit_kwh)

                unit_cost = (
                    tier.summer_cost
                    if season_label == SeasonType.SUMMER.value
                    else tier.non_summer_cost
                )

                total_cost += usage_in_tier_kwh * unit_cost
                remaining_kwh -= usage_in_tier_kwh
                last_limit_kwh = tier_end

            billing_costs[period.to_timestamp()] = total_cost

        billing_series = pd.Series(billing_costs).sort_index()
        billing_series.name = "cost"
        return billing_series

    def monthly_breakdown(
        self,
        usage_kwh: pd.Series,
        include_shares: bool = False,
    ) -> pd.DataFrame:
        if pd is None:
            raise TariffError("pandas is required for cost calculation")
        _validate_usage_series(usage_kwh)

        month_index = _month_group_index(usage_kwh.index)
        context = self.profile.evaluate(usage_kwh.index)

        if self.rates.tiered_rates:
            # For tiered rates, use billing period grouping (bimonthly for non-monthly cycles)
            billing_period_index = _billing_period_group_index(
                usage_kwh.index, self.billing_cycle_type
            )
            monthly_usage = usage_kwh.groupby(billing_period_index).sum()
            monthly_costs = self._calculate_tiered_costs(usage_kwh)
            month_seasons = (
                context["season"]
                .groupby(billing_period_index)
                .agg(lambda x: _label_value(x.mode().iloc[0]))
            )
            records = []
            for month, usage in monthly_usage.items():
                month_ts = month.to_timestamp()
                records.append(
                    {
                        "month": month_ts,
                        "season": month_seasons.loc[month],
                        "period": "tiered",
                        "usage_kwh": float(usage),
                        "cost": float(monthly_costs.loc[month_ts]),
                    }
                )
            result = pd.DataFrame(
                records,
                columns=["month", "season", "period", "usage_kwh", "cost"],
            )
            if include_shares:
                result["usage_share"] = 1.0
                result["cost_share"] = 1.0
                return result[
                    [
                        "month",
                        "season",
                        "period",
                        "usage_kwh",
                        "cost",
                        "usage_share",
                        "cost_share",
                    ]
                ]
            return result

        unit_costs = pd.Series(
            [
                self.rates.get_cost(season, period)
                for season, period in zip(context["season"], context["period"])
            ],
            index=usage_kwh.index,
        )
        base = pd.DataFrame(
            {
                "month": month_index.to_period("M"),
                "season": context["season"].apply(_label_value),
                "period": context["period"].apply(_label_value),
                "usage_kwh": usage_kwh.values,
                "cost": (usage_kwh * unit_costs).values,
            }
        )
        grouped = base.groupby(
            ["month", "season", "period"], sort=False, as_index=False
        ).sum()
        grouped["month"] = grouped["month"].dt.to_timestamp()
        if include_shares:
            month_totals = grouped.groupby("month", sort=False)[
                ["usage_kwh", "cost"]
            ].transform("sum")
            grouped["usage_share"] = grouped["usage_kwh"] / month_totals["usage_kwh"]
            grouped["cost_share"] = grouped["cost"] / month_totals["cost"]
            return grouped[
                [
                    "month",
                    "season",
                    "period",
                    "usage_kwh",
                    "cost",
                    "usage_share",
                    "cost_share",
                ]
            ]
        return grouped[["month", "season", "period", "usage_kwh", "cost"]]


def _month_group_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if index.tz is None:
        return index
    return index.tz_localize(None)


def _apportion_usage_by_season(
    usage_kwh: pd.Series,
    season_change_month: int,
    season_change_day: int,
) -> dict[str, pd.Series]:
    """將抄表期間的用電按季節變動日分攤到不同季節

    當抄表期間橫跨夏月/非夏月變動時（如 6/30），按日數比例將度數分配到不同季節。

    Args:
        usage_kwh: 用電資料
        season_change_month: 季節變動月份 (如 6)
        season_change_day: 季節變動日期 (如 30)

    Returns:
        {"before": 季節變動前的用電 Series, "after": 季節變動後的用電 Series}
    """
    if len(usage_kwh) == 0:
        return {"before": pd.Series([], dtype=float), "after": pd.Series([], dtype=float)}

    # Create change date timestamp
    year = usage_kwh.index.year[0] if hasattr(usage_kwh.index.year, '__getitem__') else usage_kwh.index.year
    change_date = pd.Timestamp(year, season_change_month, season_change_day)

    # Filter usage before and after change date
    before_mask = usage_kwh.index < change_date
    after_mask = usage_kwh.index >= change_date

    # Calculate total days in billing period
    period_start = usage_kwh.index.min()
    period_end = usage_kwh.index.max()
    total_days = (period_end - period_start).days + 1

    # Days before and after rate change
    if change_date >= period_start and change_date <= period_end:
        days_before = (change_date - period_start).days
        days_after = total_days - days_before
    elif change_date < period_start:
        # Entire period is after change date
        days_before = 0
        days_after = total_days
    else:
        # Entire period is before change date
        days_before = total_days
        days_after = 0

    # Calculate total usage
    total_usage = usage_kwh.sum()

    # Apportion usage based on days
    if days_before == 0:
        # All usage is in "after" period
        return {
            "before": pd.Series([], dtype=float),
            "after": usage_kwh,
        }
    elif days_after == 0:
        # All usage is in "before" period
        return {
            "before": usage_kwh,
            "after": pd.Series([], dtype=float),
        }

    # Apportion usage by day ratio
    apportioned_before = total_usage * days_before / total_days
    apportioned_after = total_usage * days_after / total_days

    # Create apportioned series maintaining original index structure
    before_indices = usage_kwh.index[before_mask]
    after_indices = usage_kwh.index[after_mask]

    # Create weights for apportionment
    if len(before_indices) > 0:
        before_weights = pd.Series(
            apportioned_before * usage_kwh[before_indices] / usage_kwh[before_indices].sum(),
            index=before_indices,
        )
    else:
        before_weights = pd.Series([], dtype=float, index=[])

    if len(after_indices) > 0:
        after_weights = pd.Series(
            apportioned_after * usage_kwh[after_indices] / usage_kwh[after_indices].sum(),
            index=after_indices,
        )
    else:
        after_weights = pd.Series([], dtype=float, index=[])

    return {"before": before_weights, "after": after_weights}


def _billing_period_group_index(
    index: pd.DatetimeIndex,
    cycle_type: BillingCycleType,
) -> pd.PeriodIndex:
    """根據抄表週期生成分組索引

    Args:
        index: 使用量資料的 DatetimeIndex
        cycle_type: 抄表週期型別

    Returns:
        分組用的 PeriodIndex
    """
    if cycle_type == BillingCycleType.MONTHLY:
        return index.to_period("M")

    # For bimonthly billing, we need to group pairs of months
    months = index.to_period("M")
    year = months.year.to_numpy()
    month = months.month.to_numpy()

    if cycle_type == BillingCycleType.ODD_MONTH:
        # Odd-month billing: meters read in odd months (1,3,5,7,9,11)
        # Billing periods: (12,1)->1, (2,3)->3, (4,5)->5, (6,7)->7, (8,9)->9, (10,11)->11
        # Group key is the odd month (meter reading month)
        # For month 1: group 1 (Jan meter reading for Dec-Jan period)
        # For months 2,3: group 3 (Mar meter reading for Feb-Mar period)
        # For months 4,5: group 5, etc.
        # For month 12: group 1 of next year (Dec belongs to Jan period of next year)
        dec_mask = month == 12
        # Use floor division to round down to even, then add 1
        # This gives: 2->2->3, 3->2->3, 4->4->5, 5->4->5, 6->6->7, etc.
        group = (month // 2) * 2 + 1
        # Month 1 should map to group 1, not 2
        group = np.where(month == 1, 1, group)
        # December maps to group 1 of next year
        group = np.where(dec_mask, 1, group)
        year = np.where(dec_mask, year + 1, year)
    else:  # EVEN_MONTH
        # Even-month billing: meters read in even months (2,4,6,8,10,12)
        # Billing periods: (1,2)->2, (3,4)->4, (5,6)->6, (7,8)->8, (9,10)->10, (11,12)->12
        # Group key is the even month (meter reading month)
        # No year-crossing for even-month billing (Jan+Feb are together, not Dec+Jan)
        # Formula: ceiling division to even number: ((month + 1) // 2) * 2
        group = ((month + 1) // 2) * 2

    # Build PeriodIndex by creating period strings and converting
    period_strs = [f"{int(y)}-{int(g)}" for y, g in zip(year, group)]
    return pd.PeriodIndex(period_strs, freq="M")


def _validate_usage_series(usage_kwh: pd.Series) -> None:
    if not isinstance(usage_kwh, pd.Series):
        raise InvalidUsageInput("usage must be a pandas.Series")
    if not isinstance(usage_kwh.index, pd.DatetimeIndex):
        raise InvalidUsageInput("usage index must be a pandas.DatetimeIndex")
    if usage_kwh.isna().any():
        raise InvalidUsageInput("usage series contains NaN values")
    if (usage_kwh < 0).any():
        raise InvalidUsageInput("usage values must be non-negative")
    if not usage_kwh.index.is_monotonic_increasing:
        raise InvalidUsageInput("usage timestamps must be ordered")


__all__ = [
    "ConsumptionTier",
    "DaySchedule",
    "PeriodType",
    "SeasonType",
    "TariffPlan",
    "TariffProfile",
    "TariffRate",
    "TaiwanDayTypeStrategy",
    "TaiwanSeasonStrategy",
    "TimeSlot",
    "get_period",
    "get_context",
]
