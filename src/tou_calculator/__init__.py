"""Public package entry point for the Taiwan TOU calculator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tou_calculator.billing import (
    BillingInputs,
    calculate_bill,
    calculate_bill_breakdown,
    calculate_bill_from_dict,
    calculate_bill_from_list,
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
    InvalidBasicFeeInput,
    InvalidUsageInput,
    MissingRequiredInput,
    PowerKitError,
    TariffError,
)
from tou_calculator.factory import PlanRequirements, PlanStore, TariffFactory
from tou_calculator.tariff import (
    PeriodType,
    SeasonType,
    TaiwanDayTypeStrategy,
    TaiwanSeasonStrategy,
    TariffPlan,
    TariffProfile,
    get_context,
    get_period,
)

__version__ = "0.1.0"


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


def available_plans() -> list[str]:
    """Return list of all available plan IDs.

    Use these IDs directly with `plan()`.
    """
    return list(TariffFactory().list_plans())


def plan(
    name: str,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    """Get a tariff plan by name.

    Use the plan ID returned by `available_plans()`.
    使用 `available_plans()` 返回的 plan ID。

    Args:
        name: The plan identifier (e.g., "residential_simple_2_tier")
        calendar_instance: Optional calendar instance
        cache_dir: Optional cache directory for calendar
        api_timeout: API timeout for calendar

    Returns:
        A TariffPlan instance

    Raises:
        ValueError: If plan name is not found

    Example:
        >>> plan = tou.plan("residential_simple_2_tier")
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


def get_plan_requirements(plan_name: str) -> dict[str, Any]:
    """Get the requirements for a plan.

    Returns a dict with information about what inputs are required
    for the given plan. Useful for introspection before calculating bills.

    Args:
        plan_name: The plan identifier (flexible matching supported)

    Returns:
        A dict with:
            - requires_contract_capacity: bool - Whether contract capacity is required
            - requires_meter_spec: bool - Whether meter specs are required
            - valid_basic_fee_labels: list[str] - Valid keys for basic_fee_inputs
            - uses_basic_fee_formula: bool - Whether formula-based calculation is used
            - formula_type: str | None - Type of formula if used

    Example:
        >>> reqs = get_plan_requirements("high_voltage_2_tier")
        >>> print(reqs["requires_contract_capacity"])
        True
        >>> print(reqs["valid_basic_fee_labels"])
        ['經常契約', '非夏月契約', '週六半尖峰契約', '離峰契約']
    """
    store = PlanStore()
    plan_data = store.get_plan(plan_name)
    requirements = PlanRequirements.from_plan_data(plan_data)

    return {
        "requires_contract_capacity": requirements.requires_contract_capacity,
        "requires_meter_spec": requirements.requires_meter_spec,
        "valid_basic_fee_labels": list(requirements.valid_basic_fee_labels),
        "uses_basic_fee_formula": requirements.uses_basic_fee_formula,
        "formula_type": requirements.formula_type,
    }


__all__ = [
    "TaiwanCalendar",
    "CustomCalendar",
    "TariffPlan",
    "TariffProfile",
    "PeriodType",
    "SeasonType",
    "TaiwanDayTypeStrategy",
    "TaiwanSeasonStrategy",
    "taiwan_calendar",
    "custom_calendar",
    "available_plans",
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
    "get_plan_requirements",
    "CalendarError",
    "InvalidUsageInput",
    "InvalidBasicFeeInput",
    "MissingRequiredInput",
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
    "calculate_bill_from_list",
    "calculate_bill_from_dict",
    "PlanRequirements",
    "__version__",
]
