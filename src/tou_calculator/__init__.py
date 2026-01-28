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
from tou_calculator.factory import PlanStore, TariffFactory
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


def residential_simple_2_tier_plan(
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    """Create a residential simple 2-tier TOU plan."""
    return plan(
        "residential_simple_2_tier",
        calendar_instance,
        cache_dir,
        api_timeout,
    )


def high_voltage_2_tier_plan(
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    """Create a high voltage 2-tier TOU plan."""
    return plan("high_voltage_2_tier", calendar_instance, cache_dir, api_timeout)


def residential_non_tou_plan(
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    """Create a residential non-TOU tiered plan."""
    return plan("residential_non_tou", calendar_instance, cache_dir, api_timeout)


def available_plan_ids() -> tuple[str, ...]:
    """Return list of all available plan IDs (internal use).

    For user-friendly display, use `available_plans()` which returns
    bilingual names.
    """
    return TariffFactory().list_plans()


def available_plans() -> list[str]:
    """Return list of all available plans with bilingual (EN/ZH) names."""
    store = PlanStore()
    plan_ids = store.list_plan_ids()

    # Bilingual name mapping for each plan ID
    # 雙語名稱映射
    bilingual_names = {
        "residential_non_tou": "表燈非時間電價 Residential Non-TOU",
        "lighting_non_business_tiered": "表燈非時間-住宅非營業 Non-Business Tiered",
        "lighting_business_tiered": "表燈非時間-營業用 Business Tiered",
        "residential_simple_2_tier": "簡易型二段式 Simple 2-Tier",
        "residential_simple_3_tier": "簡易型三段式 Simple 3-Tier",
        "lighting_standard_2_tier": "標準型二段式 Standard 2-Tier",
        "lighting_standard_3_tier": "標準型三段式 Standard 3-Tier",
        "low_voltage_power": "低壓電力非時間 Low Voltage Power",
        "low_voltage_2_tier": "低壓電力二段式 Low Voltage 2-Tier",
        "low_voltage_three_stage": "低壓電力三段式 Low Voltage 3-Stage",
        "low_voltage_ev": "低壓電動車 Low Voltage EV",
        "high_voltage_power": "高壓電力 High Voltage Power",
        "high_voltage_2_tier": "高壓電力二段式 High Voltage 2-Tier",
        "high_voltage_three_stage": "高壓電力三段式 High Voltage 3-Stage",
        "high_voltage_batch": "高壓批次生產 High Voltage Batch",
        "high_voltage_ev": "高壓電動車 High Voltage EV",
        "extra_high_voltage_power": "特高壓電力 Extra High Voltage Power",
        "extra_high_voltage_2_tier": "特高壓電力二段式 EHV 2-Tier",
        "extra_high_voltage_three_stage": "特高壓電力三段式 EHV 3-Stage",
        "extra_high_voltage_batch": "特高壓批次生產 EHV Batch",
    }

    return [bilingual_names.get(pid, pid) for pid in plan_ids]


def plan(
    name: str,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    """Get a tariff plan by name.

    This function uses the data-driven TariffFactory to create plans.
    Any plan defined in plans.json can be loaded.

    Args:
        name: The plan identifier
        calendar_instance: Optional calendar instance
        cache_dir: Optional cache directory for calendar
        api_timeout: API timeout for calendar

    Returns:
        A TariffPlan instance

    Raises:
        ValueError: If plan name is not found
    """
    calendar = calendar_instance or taiwan_calendar(
        cache_dir=cache_dir, api_timeout=api_timeout
    )
    try:
        return TariffFactory.create(name, calendar=calendar)
    except KeyError as exc:
        raise ValueError(f"Unsupported plan name: {name}") from exc


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
    "available_plan_ids",
    "calculate_costs",
    "get_context",
    "get_period",
    "is_holiday",
    "high_voltage_2_tier_plan",
    "residential_non_tou_plan",
    "residential_simple_2_tier_plan",
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
