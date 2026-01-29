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


def available_plan_ids() -> tuple[str, ...]:
    """Return list of all available plan IDs for use in code.

    Use these IDs with `plan()` to get a tariff plan.
    使用這些 ID 呼叫 `plan()` 來獲取電價方案。

    Returns:
        Tuple of plan ID strings (e.g., 'residential_simple_2_tier')

    Example:
        >>> ids = available_plan_ids()
        >>> plan_id = ids[0]  # e.g., 'residential_simple_2_tier'
        >>> plan = tou.plan(plan_id)
    """
    return TariffFactory().list_plans()


def available_plans() -> list[str]:
    """Return list of all available plans with bilingual (EN/ZH) names."""
    store = PlanStore()
    plan_ids = store.list_plan_ids()

    # Bilingual name mapping for each plan ID
    # 雙語名稱對映
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


def _normalize_plan_name(name: str) -> str:
    """Normalize user input to a valid plan ID.

    Accepts: English ID, Chinese name, bilingual name, with/without spaces.
    接受：英文 ID、中文、雙語、有沒有空格皆可。

    Examples:
        "residential_simple_2_tier" -> "residential_simple_2_tier"
        "residentialsimple2tier" -> "residential_simple_2_tier"
        "簡易型二段式" -> "residential_simple_2_tier"
        "Simple 2-Tier" -> "residential_simple_2_tier"
        "簡易型二段式 Simple 2-Tier" -> "residential_simple_2_tier"
    """
    # Remove all spaces and convert to lowercase for matching
    # 移除所有空格並轉小寫進行匹配
    normalized = name.replace(" ", "").lower()

    # Mapping from various input formats to plan IDs
    # 從各種輸入格式對映到 plan ID
    aliases = {
        # residential_non_tou
        "residentialnontou": "residential_non_tou",
        "residential_non_tou": "residential_non_tou",
        "表燈非時間電價": "residential_non_tou",
        "表燈非時間": "residential_non_tou",
        "residentialnon-tou": "residential_non_tou",
        "表燈非時間電價residentialnon-tou": "residential_non_tou",
        # lighting_non_business_tiered
        "lightingnonbusinesstiered": "lighting_non_business_tiered",
        "lighting_non_business_tiered": "lighting_non_business_tiered",
        "表燈非時間-住宅非營業": "lighting_non_business_tiered",
        "表燈非時間住宅非營業": "lighting_non_business_tiered",
        "non-businesstiered": "lighting_non_business_tiered",
        "非營業": "lighting_non_business_tiered",
        "表燈非時間-住宅非營業non-businesstiered": "lighting_non_business_tiered",
        # lighting_business_tiered
        "lightingbusinesstiered": "lighting_business_tiered",
        "lighting_business_tiered": "lighting_business_tiered",
        "表燈非時間-營業用": "lighting_business_tiered",
        "表燈非時間營業用": "lighting_business_tiered",
        "businesstiered": "lighting_business_tiered",
        "營業用": "lighting_business_tiered",
        "表燈非時間-營業用businesstiered": "lighting_business_tiered",
        # residential_simple_2_tier
        "residentialsimple2tier": "residential_simple_2_tier",
        "residential_simple_2_tier": "residential_simple_2_tier",
        "residentialsimpletwo-tier": "residential_simple_2_tier",
        "簡易型二段式": "residential_simple_2_tier",
        "簡易型二段": "residential_simple_2_tier",
        "simple2-tier": "residential_simple_2_tier",
        "simple2tier": "residential_simple_2_tier",
        "簡易": "residential_simple_2_tier",
        "簡易型二段式simple2-tier": "residential_simple_2_tier",
        "簡易型二段式simple2tier": "residential_simple_2_tier",
        # residential_simple_3_tier
        "residentialsimple3tier": "residential_simple_3_tier",
        "residential_simple_3_tier": "residential_simple_3_tier",
        "residentialsimplethree-tier": "residential_simple_3_tier",
        "簡易型三段式": "residential_simple_3_tier",
        "簡易型三段": "residential_simple_3_tier",
        "simple3-tier": "residential_simple_3_tier",
        "simple3tier": "residential_simple_3_tier",
        "簡易型三段式simple3-tier": "residential_simple_3_tier",
        # lighting_standard_2_tier
        "lightingstandard2tier": "lighting_standard_2_tier",
        "lighting_standard_2_tier": "lighting_standard_2_tier",
        "lightingstandardtwo-tier": "lighting_standard_2_tier",
        "標準型二段式": "lighting_standard_2_tier",
        "標準型二段": "lighting_standard_2_tier",
        "standard2-tier": "lighting_standard_2_tier",
        "standard2tier": "lighting_standard_2_tier",
        "標準二段": "lighting_standard_2_tier",
        "標準型二段式standard2-tier": "lighting_standard_2_tier",
        # lighting_standard_3_tier
        "lightingstandard3tier": "lighting_standard_3_tier",
        "lighting_standard_3_tier": "lighting_standard_3_tier",
        "lightingstandardthree-tier": "lighting_standard_3_tier",
        "標準型三段式": "lighting_standard_3_tier",
        "標準型三段": "lighting_standard_3_tier",
        "standard3-tier": "lighting_standard_3_tier",
        "standard3tier": "lighting_standard_3_tier",
        "標準三段": "lighting_standard_3_tier",
        "標準型三段式standard3-tier": "lighting_standard_3_tier",
        # low_voltage_power
        "lowvoltagepower": "low_voltage_power",
        "low_voltage_power": "low_voltage_power",
        "低壓電力非時間": "low_voltage_power",
        "低壓電力": "low_voltage_power",
        "lowvoltagenontou": "low_voltage_power",
        "低壓電力非時間lowvoltagepower": "low_voltage_power",
        # low_voltage_2_tier
        "lowvoltage2tier": "low_voltage_2_tier",
        "low_voltage_2_tier": "low_voltage_2_tier",
        "lowvoltagetwo-tier": "low_voltage_2_tier",
        "低壓電力二段式": "low_voltage_2_tier",
        "低壓二段式": "low_voltage_2_tier",
        "lowvoltage2-tier": "low_voltage_2_tier",
        "低壓電力二段式lowvoltage2-tier": "low_voltage_2_tier",
        # low_voltage_three_stage
        "lowvoltagethreestage": "low_voltage_three_stage",
        "low_voltage_three_stage": "low_voltage_three_stage",
        "低壓電力三段式": "low_voltage_three_stage",
        "低壓三段式": "low_voltage_three_stage",
        "lowvoltage3-stage": "low_voltage_three_stage",
        "低壓電力三段式lowvoltage3-stage": "low_voltage_three_stage",
        # low_voltage_ev
        "lowvoltageev": "low_voltage_ev",
        "low_voltage_ev": "low_voltage_ev",
        "低壓電動車": "low_voltage_ev",
        "低壓ev": "low_voltage_ev",
        "低壓電動車lowvoltageev": "low_voltage_ev",
        # high_voltage_power
        "highvoltagepower": "high_voltage_power",
        "high_voltage_power": "high_voltage_power",
        "高壓電力": "high_voltage_power",
        "highvoltagenontou": "high_voltage_power",
        "高壓電力highvoltagepower": "high_voltage_power",
        # high_voltage_2_tier
        "highvoltage2tier": "high_voltage_2_tier",
        "high_voltage_2_tier": "high_voltage_2_tier",
        "highvoltagetwo-tier": "high_voltage_2_tier",
        "高壓電力二段式": "high_voltage_2_tier",
        "高壓二段式": "high_voltage_2_tier",
        "highvoltage2-tier": "high_voltage_2_tier",
        "高壓電力二段式highvoltage2-tier": "high_voltage_2_tier",
        # high_voltage_three_stage
        "highvoltagethreestage": "high_voltage_three_stage",
        "high_voltage_three_stage": "high_voltage_three_stage",
        "高壓電力三段式": "high_voltage_three_stage",
        "高壓三段式": "high_voltage_three_stage",
        "highvoltage3-stage": "high_voltage_three_stage",
        "高壓電力三段式highvoltage3-stage": "high_voltage_three_stage",
        # high_voltage_batch
        "highvoltagebatch": "high_voltage_batch",
        "high_voltage_batch": "high_voltage_batch",
        "高壓批次生產": "high_voltage_batch",
        "高壓批次": "high_voltage_batch",
        "高壓批次生產highvoltagebatch": "high_voltage_batch",
        # high_voltage_ev
        "highvoltageev": "high_voltage_ev",
        "high_voltage_ev": "high_voltage_ev",
        "高壓電動車": "high_voltage_ev",
        "高壓ev": "high_voltage_ev",
        "高壓電動車highvoltageev": "high_voltage_ev",
        # extra_high_voltage_power
        "extrahighvoltagepower": "extra_high_voltage_power",
        "extra_high_voltage_power": "extra_high_voltage_power",
        "特高壓電力": "extra_high_voltage_power",
        "ehvpower": "extra_high_voltage_power",
        "特高壓": "extra_high_voltage_power",
        "特高壓電力extrahighvoltagepower": "extra_high_voltage_power",
        # extra_high_voltage_2_tier
        "extrahighvoltage2tier": "extra_high_voltage_2_tier",
        "extra_high_voltage_2_tier": "extra_high_voltage_2_tier",
        "extrahighvoltagetwo-tier": "extra_high_voltage_2_tier",
        "特高壓電力二段式": "extra_high_voltage_2_tier",
        "特高壓二段式": "extra_high_voltage_2_tier",
        "ehv2-tier": "extra_high_voltage_2_tier",
        "ehv2tier": "extra_high_voltage_2_tier",
        "特高壓電力二段式ehv2-tier": "extra_high_voltage_2_tier",
        # extra_high_voltage_three_stage
        "extrahighvoltagethreestage": "extra_high_voltage_three_stage",
        "extra_high_voltage_three_stage": "extra_high_voltage_three_stage",
        "特高壓電力三段式": "extra_high_voltage_three_stage",
        "特高壓三段式": "extra_high_voltage_three_stage",
        "ehv3-stage": "extra_high_voltage_three_stage",
        "特高壓電力三段式ehv3-stage": "extra_high_voltage_three_stage",
        # extra_high_voltage_batch
        "extrahighvoltagebatch": "extra_high_voltage_batch",
        "extra_high_voltage_batch": "extra_high_voltage_batch",
        "特高壓批次生產": "extra_high_voltage_batch",
        "特高壓批次": "extra_high_voltage_batch",
        "ehvbatch": "extra_high_voltage_batch",
        "特高壓批次生產ehvbatch": "extra_high_voltage_batch",
    }

    # Direct match
    if normalized in aliases:
        return aliases[normalized]

    # Try exact match with original name (for standard plan IDs)
    store = PlanStore()
    valid_ids = store.list_plan_ids()
    if name in valid_ids:
        return name

    # Try exact match after removing spaces
    no_space = name.replace(" ", "")
    if no_space in valid_ids:
        return no_space

    # Fuzzy match: check if normalized is a substring of any valid ID
    for plan_id in valid_ids:
        if normalized == plan_id.replace(" ", "").replace("_", ""):
            return plan_id
        if normalized in plan_id.replace("_", ""):
            return plan_id

    # Try matching against bilingual names
    bilingual_names = {
        "residential_non_tou": [
            "表燈非時間電價",
            "residential non-tou",
            "非時間電價",
        ],
        "lighting_non_business_tiered": [
            "表燈非時間-住宅非營業",
            "lighting non-business tiered",
            "非營業",
        ],
        "lighting_business_tiered": [
            "表燈非時間-營業用",
            "lighting business tiered",
            "營業用",
        ],
        "residential_simple_2_tier": [
            "簡易型二段式",
            "residential simple 2-tier",
            "simple 2-tier",
            "簡易型二段",
            "simple 2 tier",
            "簡易型",
        ],
        "residential_simple_3_tier": [
            "簡易型三段式",
            "residential simple 3-tier",
            "simple 3-tier",
            "簡易型三段",
            "simple 3 tier",
        ],
        "lighting_standard_2_tier": [
            "標準型二段式",
            "lighting standard 2-tier",
            "standard 2-tier",
            "標準型二段",
            "standard 2 tier",
            "標準二段",
        ],
        "lighting_standard_3_tier": [
            "標準型三段式",
            "lighting standard 3-tier",
            "standard 3-tier",
            "標準型三段",
            "standard 3 tier",
            "標準三段",
        ],
        "low_voltage_power": [
            "低壓電力非時間",
            "low voltage power",
            "低壓電力",
        ],
        "low_voltage_2_tier": [
            "低壓電力二段式",
            "low voltage 2-tier",
            "low voltage 2 tier",
            "低壓二段式",
        ],
        "low_voltage_three_stage": [
            "低壓電力三段式",
            "low voltage 3-stage",
            "low voltage 3 stage",
            "低壓三段式",
        ],
        "low_voltage_ev": ["低壓電動車", "low voltage ev", "低壓 ev"],
        "high_voltage_power": [
            "高壓電力",
            "high voltage power",
            "高壓電力非時間",
        ],
        "high_voltage_2_tier": [
            "高壓電力二段式",
            "high voltage 2-tier",
            "high voltage 2 tier",
            "高壓二段式",
        ],
        "high_voltage_three_stage": [
            "高壓電力三段式",
            "high voltage 3-stage",
            "high voltage 3 stage",
            "高壓三段式",
        ],
        "high_voltage_batch": [
            "高壓批次生產",
            "high voltage batch",
            "高壓批次",
        ],
        "high_voltage_ev": ["高壓電動車", "high voltage ev", "高壓 ev"],
        "extra_high_voltage_power": [
            "特高壓電力",
            "extra high voltage power",
            "特高壓",
            "ehv power",
        ],
        "extra_high_voltage_2_tier": [
            "特高壓電力二段式",
            "extra high voltage 2-tier",
            "ehv 2-tier",
            "特高壓二段式",
        ],
        "extra_high_voltage_three_stage": [
            "特高壓電力三段式",
            "extra high voltage 3-stage",
            "ehv 3-stage",
            "特高壓三段式",
        ],
        "extra_high_voltage_batch": [
            "特高壓批次生產",
            "extra high voltage batch",
            "特高壓批次",
            "ehv batch",
        ],
    }

    for plan_id, variations in bilingual_names.items():
        for variation in variations:
            if normalized == variation.replace(" ", "").lower():
                return plan_id

    # If no match found, return original name and let the factory handle the error
    return name


def plan(
    name: str,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
) -> TariffPlan:
    """Get a tariff plan by name.

    This function uses the data-driven TariffFactory to create plans.
    Any plan defined in plans.json can be loaded.

    Accepts flexible name formats:
    - English ID: "residential_simple_2_tier"
    - Chinese name: "簡易型二段式"
    - Bilingual: "簡易型二段式 Simple 2-Tier"
    - With/without spaces: "simple 2 tier" or "simple2tier"

    接受靈活的名稱格式：
    - 英文 ID："residential_simple_2_tier"
    - 中文名稱："簡易型二段式"
    - 雙語："簡易型二段式 Simple 2-Tier"
    - 有無空格："simple 2 tier" 或 "simple2tier"

    Args:
        name: The plan identifier (flexible matching)
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
    normalized_name = _normalize_plan_name(name)
    try:
        return TariffFactory.create(normalized_name, calendar=calendar)
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
    plan_id = _normalize_plan_name(plan_name)
    plan_data = store.get_plan(plan_id)
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
