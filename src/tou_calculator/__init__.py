"""Public package entry point for the Taiwan TOU calculator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tou_calculator.billing import (
    BillingInputs,
    calculate_bill,
    calculate_bill_breakdown,
    calculate_bill_simple,
)
from tou_calculator.calendar import TaiwanCalendar, taiwan_calendar
from tou_calculator.custom import (
    CustomCalendar,
    WeekdayDayTypeStrategy,
    build_day_schedule,
    build_tariff_plan,
    build_tariff_profile,
    build_tariff_rate,
    custom_calendar,
)
from tou_calculator.errors import (
    CalendarError,
    InvalidUsageInput,
    PowerKitError,
    TariffError,
)
from tou_calculator.tariff import (
    PeriodType,
    SeasonType,
    TaipowerTariffs,
    TaiwanDayTypeStrategy,
    TaiwanSeasonStrategy,
    TariffPlan,
    TariffProfile,
    get_context,
    get_period,
)

__version__ = "0.1.0"


def taipower_tariffs(
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TaipowerTariffs:
    calendar_value = calendar_instance or taiwan_calendar(
        cache_dir=cache_dir,
        api_timeout=api_timeout,
    )
    return TaipowerTariffs(calendar_value)


def calculate_costs(usage: Any, plan: TariffPlan) -> Any:
    return plan.calculate_costs(usage)


def is_holiday(
    target: object,
    calendar: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> bool:
    calendar_instance = calendar or taiwan_calendar(
        cache_dir=cache_dir, api_timeout=api_timeout
    )
    return calendar_instance.is_holiday(target)


def residential_simple_two_stage_plan(
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    plan = taipower_tariffs(
        calendar_instance,
        cache_dir,
        api_timeout,
    ).get_residential_simple_two_stage_plan()
    return TariffPlan(plan.profile, plan.rates)


def high_voltage_two_stage_plan(
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    plan = taipower_tariffs(
        calendar_instance,
        cache_dir,
        api_timeout,
    ).get_high_voltage_two_stage_plan()
    return TariffPlan(plan.profile, plan.rates)


def residential_non_tou_plan(
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    plan = taipower_tariffs(
        calendar_instance,
        cache_dir,
        api_timeout,
    ).get_residential_non_tou_plan()
    return TariffPlan(plan.profile, plan.rates)


def available_plans() -> list[str]:
    return [
        "high_voltage_two_stage",
        "residential_non_tou",
        "residential_simple_two_stage",
    ]


def plan(
    name: str,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    if name == "residential_simple_two_stage":
        return residential_simple_two_stage_plan(
            calendar_instance, cache_dir, api_timeout
        )
    if name == "high_voltage_two_stage":
        return high_voltage_two_stage_plan(calendar_instance, cache_dir, api_timeout)
    if name == "residential_non_tou":
        return residential_non_tou_plan(calendar_instance, cache_dir, api_timeout)
    raise ValueError(f"Unsupported plan name: {name}")


def period_at(
    target: object,
    plan_name: str,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> Any:
    selected_plan = plan(plan_name, calendar_instance, cache_dir, api_timeout)
    return get_period(target, selected_plan.profile)


def period_context(
    target: object,
    plan_name: str,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> Any:
    selected_plan = plan(plan_name, calendar_instance, cache_dir, api_timeout)
    return get_context(target, selected_plan.profile)


def costs(
    usage: Any,
    plan_name: str,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> Any:
    selected_plan = plan(plan_name, calendar_instance, cache_dir, api_timeout)
    return calculate_costs(usage, selected_plan)


def monthly_breakdown(
    usage: Any,
    plan_name: str,
    include_shares: bool = False,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> Any:
    selected_plan = plan(plan_name, calendar_instance, cache_dir, api_timeout)
    return selected_plan.monthly_breakdown(usage, include_shares=include_shares)


def plan_details(
    plan_name: str,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> dict[str, Any]:
    selected_plan = plan(plan_name, calendar_instance, cache_dir, api_timeout)
    return selected_plan.describe()


def pricing_context(
    target: object,
    plan_name: str,
    usage: Any = None,
    include_details: bool = False,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> Any:
    selected_plan = plan(plan_name, calendar_instance, cache_dir, api_timeout)
    return selected_plan.pricing_context(
        target,
        usage_kwh=usage,
        include_details=include_details,
    )


__all__ = [
    "TaiwanCalendar",
    "CustomCalendar",
    "TaipowerTariffs",
    "TariffPlan",
    "TariffProfile",
    "PeriodType",
    "SeasonType",
    "TaiwanDayTypeStrategy",
    "TaiwanSeasonStrategy",
    "taiwan_calendar",
    "custom_calendar",
    "taipower_tariffs",
    "available_plans",
    "calculate_costs",
    "get_context",
    "get_period",
    "is_holiday",
    "high_voltage_two_stage_plan",
    "residential_non_tou_plan",
    "residential_simple_two_stage_plan",
    "period_at",
    "period_context",
    "pricing_context",
    "plan",
    "plan_details",
    "costs",
    "monthly_breakdown",
    "CalendarError",
    "InvalidUsageInput",
    "PowerKitError",
    "TariffError",
    "WeekdayDayTypeStrategy",
    "build_day_schedule",
    "build_tariff_plan",
    "build_tariff_profile",
    "build_tariff_rate",
    "BillingInputs",
    "calculate_bill",
    "calculate_bill_breakdown",
    "calculate_bill_simple",
    "__version__",
]
