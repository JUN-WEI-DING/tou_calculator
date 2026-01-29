"""Billing utilities based on plans.json rules."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from tou_calculator.calendar import TaiwanCalendar, taiwan_calendar
from tou_calculator.errors import (
    InvalidBasicFeeInput,
    InvalidUsageInput,
    MissingRequiredInput,
)
from tou_calculator.factory import (
    PlanRequirements,
    PlanStore,
    _build_tariff_plan_from_data,
    _season_strategy,
)


@dataclass
class BillingInputs:
    basic_fee_inputs: dict[str, float] = field(default_factory=dict)
    power_factor: float | None = None
    contract_capacity_kw: float | None = None
    over_contract_kw: float | None = None
    contract_capacities: dict[str, float] = field(default_factory=dict)
    demand_kw: pd.Series | None = None
    meter_phase: str | None = None
    meter_voltage_v: int | None = None
    meter_ampere: float | None = None
    billing_cycle_months: int | None = None
    demand_adjustment_factor: float = 1.0

    @classmethod
    def for_high_voltage(
        cls,
        regular: float,
        non_summer: float,
        saturday_semi_peak: float,
        off_peak: float,
        power_factor: float | None = None,
        demand_kw: pd.Series | None = None,
        demand_adjustment_factor: float = 1.0,
    ) -> BillingInputs:
        """Create inputs for high voltage two-stage TOU plans.

        Args:
            regular: Regular contract capacity (kW)
            non_summer: Non-summer contract capacity (kW)
            saturday_semi_peak: Saturday semi-peak contract capacity (kW)
            off_peak: Off-peak contract capacity (kW)
            power_factor: Optional power factor percentage
            demand_kw: Optional demand series for penalty calculation
            demand_adjustment_factor: Adjustment factor for demand data

        Example:
            inputs = BillingInputs.for_high_voltage(
                regular=100,
                non_summer=50,
                saturday_semi_peak=30,
                off_peak=20,
            )
        """
        return cls(
            contract_capacities={
                "regular": regular,
                "non_summer": non_summer,
                "saturday_semi_peak": saturday_semi_peak,
                "off_peak": off_peak,
            },
            power_factor=power_factor,
            demand_kw=demand_kw,
            demand_adjustment_factor=demand_adjustment_factor,
        )

    @classmethod
    def for_high_voltage_three_stage(
        cls,
        regular: float,
        semi_peak: float,
        saturday_semi_peak: float,
        off_peak: float,
        power_factor: float | None = None,
        demand_kw: pd.Series | None = None,
        demand_adjustment_factor: float = 1.0,
    ) -> BillingInputs:
        """Create inputs for high voltage three-stage TOU plans.

        Args:
            regular: Regular contract capacity (kW)
            semi_peak: Semi-peak contract capacity (kW)
            saturday_semi_peak: Saturday semi-peak contract capacity (kW)
            off_peak: Off-peak contract capacity (kW)
            power_factor: Optional power factor percentage
            demand_kw: Optional demand series for penalty calculation
            demand_adjustment_factor: Adjustment factor for demand data
        """
        return cls(
            contract_capacities={
                "regular": regular,
                "semi_peak": semi_peak,
                "saturday_semi_peak": saturday_semi_peak,
                "off_peak": off_peak,
            },
            power_factor=power_factor,
            demand_kw=demand_kw,
            demand_adjustment_factor=demand_adjustment_factor,
        )

    @classmethod
    def for_extra_high_voltage(
        cls,
        regular: float,
        non_summer: float,
        saturday_semi_peak: float,
        off_peak: float,
        power_factor: float | None = None,
        demand_kw: pd.Series | None = None,
        demand_adjustment_factor: float = 1.0,
    ) -> BillingInputs:
        """Create inputs for extra high voltage two-stage TOU plans.

        Args:
            regular: Regular contract capacity (kW)
            non_summer: Non-summer contract capacity (kW)
            saturday_semi_peak: Saturday semi-peak contract capacity (kW)
            off_peak: Off-peak contract capacity (kW)
            power_factor: Optional power factor percentage
            demand_kw: Optional demand series for penalty calculation
            demand_adjustment_factor: Adjustment factor for demand data
        """
        return cls(
            contract_capacities={
                "regular": regular,
                "non_summer": non_summer,
                "saturday_semi_peak": saturday_semi_peak,
                "off_peak": off_peak,
            },
            power_factor=power_factor,
            demand_kw=demand_kw,
            demand_adjustment_factor=demand_adjustment_factor,
        )

    @classmethod
    def for_extra_high_voltage_three_stage(
        cls,
        regular: float,
        semi_peak: float,
        saturday_semi_peak: float,
        off_peak: float,
        power_factor: float | None = None,
        demand_kw: pd.Series | None = None,
        demand_adjustment_factor: float = 1.0,
    ) -> BillingInputs:
        """Create inputs for extra high voltage three-stage TOU plans.

        Args:
            regular: Regular contract capacity (kW)
            semi_peak: Semi-peak contract capacity (kW)
            saturday_semi_peak: Saturday semi-peak contract capacity (kW)
            off_peak: Off-peak contract capacity (kW)
            power_factor: Optional power factor percentage
            demand_kw: Optional demand series for penalty calculation
            demand_adjustment_factor: Adjustment factor for demand data
        """
        return cls(
            contract_capacities={
                "regular": regular,
                "semi_peak": semi_peak,
                "saturday_semi_peak": saturday_semi_peak,
                "off_peak": off_peak,
            },
            power_factor=power_factor,
            demand_kw=demand_kw,
            demand_adjustment_factor=demand_adjustment_factor,
        )

    @classmethod
    def for_residential(
        cls,
        phase: str,
        voltage: int,
        ampere: float,
        basic_fee_multiplier: float = 1.0,
    ) -> BillingInputs:
        """Create inputs for residential plans with meter specification.

        Args:
            phase: Meter phase ("single" or "three")
            voltage: Voltage level (110, 220, or other valid voltage)
            ampere: Amperage rating
            basic_fee_multiplier: Multiplier for per-household fees (default 1.0)

        Example:
            inputs = BillingInputs.for_residential(
                phase="single",
                voltage=110,
                ampere=10,
            )
        """
        return cls(
            meter_phase=phase,
            meter_voltage_v=voltage,
            meter_ampere=ampere,
            basic_fee_inputs={"basic_fee": basic_fee_multiplier},
        )

    @classmethod
    def for_lighting_standard(
        cls,
        phase: str,
        contract_kw: float,
        household_count: float = 1.0,
    ) -> BillingInputs:
        """Create inputs for standard lighting TOU plans with contract capacity.

        Args:
            phase: Meter phase for per-household fee ("single" or "three")
            contract_kw: Contract capacity in kW
            household_count: Number of households (default 1.0)
        """
        label = "按戶計收-單相" if phase == "single" else "按戶計收-三相"
        return cls(
            contract_capacity_kw=contract_kw,
            basic_fee_inputs={label: household_count, "經常契約": contract_kw},
        )


def _get_required_capacities_for_formula(formula_type: str) -> set[str]:
    """Return required contract_capacities keys for each formula type."""
    if formula_type == "two_stage":
        return {"regular", "non_summer", "saturday_semi_peak", "off_peak"}
    if formula_type == "three_stage":
        return {"regular", "semi_peak", "saturday_semi_peak", "off_peak"}
    if formula_type == "regular_only":
        return {"regular"}
    return set()


def _validate_billing_inputs(
    plan_data: dict[str, Any],
    inputs: BillingInputs,
    strict: bool = False,
) -> list[str]:
    """Validate billing inputs and return warnings.

    Args:
        plan_data: The plan's JSON data
        inputs: User-provided billing inputs
        strict: If True, raise errors on unknown keys and missing optional fields

    Returns:
        A list of warning messages for non-strict validation issues

    Raises:
        MissingRequiredInput: If required inputs are missing
        InvalidBasicFeeInput: If basic_fee_inputs has invalid keys (strict mode)
    """
    requirements = PlanRequirements.from_plan_data(plan_data)
    warnings = []

    # 1. Check contract capacity requirement (critical - always enforced)
    if requirements.requires_contract_capacity:
        has_capacity = (
            inputs.contract_capacity_kw is not None or inputs.contract_capacities
        )
        if not has_capacity:
            raise MissingRequiredInput(
                f"Plan '{plan_data.get('id')}' requires contract capacity. "
                f"Provide either contract_capacity_kw or contract_capacities. "
                f"Use BillingInputs.for_high_voltage() or "
                f"BillingInputs.for_extra_high_voltage() for convenient setup."
            )

    # 2. Validate basic_fee_inputs keys
    if inputs.basic_fee_inputs:
        unknown_keys = (
            set(inputs.basic_fee_inputs.keys()) - requirements.valid_basic_fee_labels
        )
        if unknown_keys:
            if strict:
                raise InvalidBasicFeeInput(
                    f"Unknown keys in basic_fee_inputs: {unknown_keys}. "
                    f"Valid keys for this plan: {requirements.valid_basic_fee_labels}"
                )
            warnings.append(
                f"Unknown keys in basic_fee_inputs (ignored): {unknown_keys}"
            )

    # 3. For formula-based plans, validate required capacities
    if requirements.uses_basic_fee_formula and requirements.formula_type:
        required_caps = _get_required_capacities_for_formula(requirements.formula_type)
        provided_caps = set(inputs.contract_capacities.keys())
        missing_caps = required_caps - provided_caps

        if missing_caps:
            # In strict mode, this is an error
            if strict:
                raise MissingRequiredInput(
                    f"Formula type '{requirements.formula_type}' requires "
                    f"contract_capacities with keys: {required_caps}. "
                    f"Missing: {missing_caps}. "
                    f"Use BillingInputs.for_high_voltage() or similar factory method."
                )
            # In non-strict mode, warn
            warnings.append(
                f"Formula may require contract_capacities keys: {missing_caps}"
            )

    # 4. Check meter spec requirement for minimum usage rules
    if requirements.requires_meter_spec:
        if not all([inputs.meter_phase, inputs.meter_voltage_v, inputs.meter_ampere]):
            if strict:
                raise MissingRequiredInput(
                    f"Plan '{plan_data.get('id')}' has minimum usage rules. "
                    f"Providing meter_phase, meter_voltage_v, and meter_ampere "
                    f"is required for accurate billing. "
                    f"Use BillingInputs.for_residential() for convenient setup."
                )
            warnings.append(
                f"Plan '{plan_data.get('id')}' has minimum usage rules. "
                f"Providing meter specifications is recommended."
            )

    return warnings


def calculate_bill(
    usage: pd.Series,
    plan_id: str,
    inputs: BillingInputs | None = None,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
    strict: bool = False,
) -> pd.DataFrame:
    if not isinstance(usage, pd.Series):
        raise InvalidUsageInput("usage must be a pandas.Series")
    if not isinstance(usage.index, pd.DatetimeIndex):
        raise InvalidUsageInput("usage index must be a pandas.DatetimeIndex")

    inputs = inputs or BillingInputs()
    store = PlanStore()
    plan_data = store.resolve_plan(plan_id)

    # Validate inputs against plan requirements
    validation_warnings = _validate_billing_inputs(plan_data, inputs, strict=strict)
    for warning in validation_warnings:
        warnings.warn(warning, UserWarning, stacklevel=2)

    calendar = calendar_instance or taiwan_calendar(
        cache_dir=cache_dir, api_timeout=api_timeout
    )

    if inputs.billing_cycle_months is None:
        inputs.billing_cycle_months = plan_data.get("billing_rules", {}).get(
            "billing_cycle_months"
        )

    usage_for_billing = _apply_minimum_usage(plan_data, store, usage, inputs)
    billing_periods = _billing_period_index(
        usage_for_billing.index, inputs.billing_cycle_months
    )

    tariff_plan = _build_tariff_plan_from_data(
        plan_data,
        store,
        calendar,
        billing_cycle_months=inputs.billing_cycle_months,
    )
    context = tariff_plan.profile.evaluate(usage_for_billing.index)
    energy_costs = _calculate_energy_costs(
        usage_for_billing,
        context,
        billing_periods,
        tariff_plan,
    )

    month_index = energy_costs.index
    monthly_usage = usage_for_billing.groupby(billing_periods).sum()
    monthly_usage.index = monthly_usage.index.to_timestamp()

    basic_costs = _calculate_basic_fees(plan_data, inputs, month_index, store)
    surcharge = _calculate_surcharges(plan_data, inputs, monthly_usage)
    adjustment = _calculate_adjustments(
        plan_data,
        inputs,
        basic_costs,
        month_index,
        store,
        context,
        billing_periods,
        energy_costs,
        surcharge,
    )

    total = energy_costs + basic_costs + surcharge + adjustment
    min_fee = _minimum_monthly_fee(plan_data)
    if min_fee is not None:
        total = total.clip(lower=min_fee)

    return pd.DataFrame(
        {
            "energy_cost": energy_costs,
            "basic_cost": basic_costs,
            "surcharge": surcharge,
            "adjustment": adjustment,
            "total": total,
        }
    )


def calculate_bill_simple(
    usage: pd.Series,
    plan_id: str,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
    strict: bool = False,
) -> pd.DataFrame:
    return calculate_bill(
        usage,
        plan_id,
        inputs=None,
        calendar_instance=calendar_instance,
        cache_dir=cache_dir,
        api_timeout=api_timeout,
        strict=strict,
    )


def calculate_bill_breakdown(
    usage: pd.Series,
    plan_id: str,
    inputs: BillingInputs | None = None,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
    strict: bool = False,
) -> dict[str, pd.DataFrame]:
    if not isinstance(usage, pd.Series):
        raise InvalidUsageInput("usage must be a pandas.Series")
    if not isinstance(usage.index, pd.DatetimeIndex):
        raise InvalidUsageInput("usage index must be a pandas.DatetimeIndex")

    inputs = inputs or BillingInputs()
    store = PlanStore()
    plan_data = store.resolve_plan(plan_id)

    # Validate inputs against plan requirements
    validation_warnings = _validate_billing_inputs(plan_data, inputs, strict=strict)
    for warning in validation_warnings:
        warnings.warn(warning, UserWarning, stacklevel=2)

    calendar = calendar_instance or taiwan_calendar(
        cache_dir=cache_dir, api_timeout=api_timeout
    )

    if inputs.billing_cycle_months is None:
        inputs.billing_cycle_months = plan_data.get("billing_rules", {}).get(
            "billing_cycle_months"
        )

    usage_for_billing = _apply_minimum_usage(plan_data, store, usage, inputs)
    billing_periods = _billing_period_index(
        usage_for_billing.index, inputs.billing_cycle_months
    )

    tariff_plan = _build_tariff_plan_from_data(
        plan_data,
        store,
        calendar,
        billing_cycle_months=inputs.billing_cycle_months,
    )
    context = tariff_plan.profile.evaluate(usage_for_billing.index)

    energy_costs = _calculate_energy_costs(
        usage_for_billing,
        context,
        billing_periods,
        tariff_plan,
    )
    month_index = energy_costs.index

    monthly_usage = usage_for_billing.groupby(billing_periods).sum()
    monthly_usage.index = monthly_usage.index.to_timestamp()

    basic_costs, basic_details = _calculate_basic_fees_breakdown(
        plan_data,
        inputs,
        month_index,
        store,
    )
    surcharge = _calculate_surcharges(plan_data, inputs, monthly_usage)
    adjustment, adjustment_details = _calculate_adjustments_breakdown(
        plan_data,
        inputs,
        basic_costs,
        month_index,
        store,
        context,
        billing_periods,
        energy_costs,
        surcharge,
    )

    total = energy_costs + basic_costs + surcharge + adjustment
    min_fee = _minimum_monthly_fee(plan_data)
    if min_fee is not None:
        min_adjustment = (min_fee - total).clip(lower=0.0)
        total = total.clip(lower=min_fee)
    else:
        min_adjustment = pd.Series(0.0, index=total.index)

    summary = pd.DataFrame(
        {
            "energy_cost": energy_costs,
            "basic_cost": basic_costs,
            "surcharge": surcharge,
            "adjustment": adjustment,
            "min_fee_adjustment": min_adjustment,
            "total": total,
        }
    )

    period_usage = usage_for_billing.groupby(
        [billing_periods, context["season"], context["period"]]
    ).sum()
    period_usage.index = period_usage.index.set_names(
        ["period", "season", "period_type"]
    )
    period_usage = period_usage.reset_index()
    period_usage["period"] = period_usage["period"].dt.to_timestamp()
    period_usage = period_usage.rename(columns={0: "usage_kwh"})

    period_costs = _calculate_period_costs(
        usage_for_billing,
        context,
        billing_periods,
        tariff_plan,
    )
    period_costs = period_costs.reset_index()
    period_costs = period_costs.rename(columns={0: "energy_cost"})
    details = period_usage.merge(
        period_costs,
        on=["period", "season", "period_type"],
        how="left",
    )

    return {
        "summary": summary,
        "details": details,
        "basic_details": basic_details,
        "adjustment_details": adjustment_details,
    }


def _month_season_label(
    month_index: pd.Index,
    plan_data: dict[str, Any],
    store: PlanStore,
) -> list[str]:
    season_strategy = _season_strategy(plan_data, store)
    labels = []
    for ts in month_index:
        day = date(ts.year, ts.month, 1)
        season = season_strategy.get_season(day)
        labels.append(season.value if hasattr(season, "value") else str(season))
    return labels


def _calculate_basic_fees(
    plan_data: dict[str, Any],
    inputs: BillingInputs,
    month_index: pd.Index,
    store: PlanStore,
) -> pd.Series:
    rules = plan_data.get("billing_rules", {})
    formula = rules.get("basic_fee_formula")
    season_labels = _month_season_label(month_index, plan_data, store)
    monthly = pd.Series(0.0, index=month_index)
    if formula and inputs.contract_capacities:
        basic_fee_result = _basic_fee_from_formula(
            plan_data, inputs, month_index, store, formula, detailed=False
        )
        # _basic_fee_from_formula always returns (monthly, details) tuple
        monthly = (
            basic_fee_result[0]
            if isinstance(basic_fee_result, tuple)
            else basic_fee_result
        )
    else:
        basic_fee = plan_data.get("basic_fee")
        if basic_fee is not None:
            count = inputs.basic_fee_inputs.get("basic_fee", 1.0)
            monthly += float(basic_fee) * count

        for entry in plan_data.get("basic_fees", []):
            label = entry.get("label", "")
            unit = entry.get("unit", "")
            if unit == "per_household_month":
                quantity = inputs.basic_fee_inputs.get(label, 1.0)
            else:
                quantity = inputs.basic_fee_inputs.get(label, 0.0)
            if quantity == 0:
                continue
            for idx, season_label in enumerate(season_labels):
                if "summer" in entry or "non_summer" in entry:
                    rate = (
                        entry.get("summer")
                        if season_label == "summer"
                        else entry.get("non_summer")
                    )
                else:
                    rate = entry.get("cost")
                if rate is None:
                    continue
                monthly.iloc[idx] += float(rate) * quantity

    if inputs.billing_cycle_months and inputs.billing_cycle_months > 1:
        monthly = monthly * inputs.billing_cycle_months

    return monthly


def _calculate_basic_fees_breakdown(
    plan_data: dict[str, Any],
    inputs: BillingInputs,
    month_index: pd.Index,
    store: PlanStore,
) -> tuple[pd.Series, pd.DataFrame]:
    rules = plan_data.get("billing_rules", {})
    formula = rules.get("basic_fee_formula")
    season_labels = _month_season_label(month_index, plan_data, store)
    monthly = pd.Series(0.0, index=month_index)
    details: list[dict[str, Any]] = []

    if formula and inputs.contract_capacities:
        base_series, base_details = _basic_fee_from_formula(
            plan_data,
            inputs,
            month_index,
            store,
            formula,
            detailed=True,
        )
        monthly += base_series
        details.extend(base_details)
    else:
        basic_fee = plan_data.get("basic_fee")
        if basic_fee is not None:
            count = inputs.basic_fee_inputs.get("basic_fee", 1.0)
            value = float(basic_fee) * count
            monthly += value
            for ts in month_index:
                details.append(
                    {
                        "period": ts,
                        "label": "basic_fee",
                        "quantity": count,
                        "rate": float(basic_fee),
                        "cost": value,
                    }
                )

        for entry in plan_data.get("basic_fees", []):
            label = entry.get("label", "")
            unit = entry.get("unit", "")
            if unit == "per_household_month":
                quantity = inputs.basic_fee_inputs.get(label, 1.0)
            else:
                quantity = inputs.basic_fee_inputs.get(label, 0.0)
            if quantity == 0:
                continue
            for idx, season_label in enumerate(season_labels):
                if "summer" in entry or "non_summer" in entry:
                    rate = (
                        entry.get("summer")
                        if season_label == "summer"
                        else entry.get("non_summer")
                    )
                else:
                    rate = entry.get("cost")
                if rate is None:
                    continue
                cost = float(rate) * quantity
                monthly.iloc[idx] += cost
                details.append(
                    {
                        "period": month_index[idx],
                        "label": label,
                        "quantity": quantity,
                        "rate": float(rate),
                        "cost": cost,
                    }
                )

    if inputs.billing_cycle_months and inputs.billing_cycle_months > 1:
        monthly = monthly * inputs.billing_cycle_months
        for item in details:
            item["cost"] = float(item["cost"]) * inputs.billing_cycle_months

    return monthly, pd.DataFrame(details)


def _calculate_surcharges(
    plan_data: dict[str, Any],
    inputs: BillingInputs,
    monthly_usage: pd.Series,
) -> pd.Series:
    rules = plan_data.get("billing_rules", {})
    rule = rules.get("over_2000_kwh_surcharge") or plan_data.get(
        "over_2000_kwh_surcharge"
    )
    surcharge = pd.Series(0.0, index=monthly_usage.index)
    if rule:
        threshold = rule.get("threshold_kwh", 2000)
        cost = rule.get("cost_per_kwh", 0.0)
        over = (monthly_usage - threshold).clip(lower=0.0)
        surcharge += over * cost
    return surcharge


def _calculate_adjustments(
    plan_data: dict[str, Any],
    inputs: BillingInputs,
    basic_costs: pd.Series,
    month_index: pd.Index,
    store: PlanStore,
    context_df: pd.DataFrame,
    billing_periods: pd.PeriodIndex,
    energy_costs: pd.Series,
    surcharge: pd.Series,
) -> pd.Series:
    return _calculate_adjustments_breakdown(
        plan_data,
        inputs,
        basic_costs,
        month_index,
        store,
        context_df,
        billing_periods,
        energy_costs,
        surcharge,
    )[0]


def _calculate_adjustments_breakdown(
    plan_data: dict[str, Any],
    inputs: BillingInputs,
    basic_costs: pd.Series,
    month_index: pd.Index,
    store: PlanStore,
    context_df: pd.DataFrame,
    billing_periods: pd.PeriodIndex,
    energy_costs: pd.Series,
    surcharge: pd.Series,
) -> tuple[pd.Series, pd.DataFrame]:
    rules = plan_data.get("billing_rules", {})
    adjustment = pd.Series(0.0, index=month_index)
    details: list[dict[str, Any]] = []

    pf_rule = rules.get("power_factor_adjustment")
    if pf_rule and inputs.power_factor is not None:
        base = pf_rule.get("base_percent", 80)
        max_discount = pf_rule.get("max_discount_percent", 95)
        step = pf_rule.get("step_percent", 0.1)
        apply_to = pf_rule.get("apply_to", "basic")
        pf = float(inputs.power_factor)
        if apply_to == "total":
            target = basic_costs + energy_costs + surcharge
        elif apply_to == "energy":
            target = energy_costs
        else:
            target = basic_costs
        if pf < base:
            delta = base - pf
            delta_cost = target * (delta * step / 100.0)
            adjustment += delta_cost
            for idx, value in delta_cost.items():
                details.append(
                    {
                        "period": idx,
                        "type": "power_factor",
                        "amount": float(value),
                    }
                )
        elif pf > base:
            cap = min(pf, max_discount)
            delta = cap - base
            delta_cost = -target * (delta * step / 100.0)
            adjustment += delta_cost
            for idx, value in delta_cost.items():
                details.append(
                    {
                        "period": idx,
                        "type": "power_factor",
                        "amount": float(value),
                    }
                )

    oc_rule = rules.get("over_contract_penalty")
    if oc_rule:
        base_label = oc_rule.get("base_fee_label", "經常契約")
        base_rate = _basic_fee_rate_for_label(plan_data, base_label, month_index, store)
        if base_rate is not None:
            over_series = _compute_over_contract_kw(
                inputs,
                context_df,
                billing_periods,
                oc_rule,
            )
            if over_series is not None:
                threshold_ratio = oc_rule.get("threshold_ratio", 0.10)
                rate_low = oc_rule.get("rate_low", 2)
                rate_high = oc_rule.get("rate_high", 3)
                for idx, over in over_series.items():
                    contract_kw = (
                        inputs.contract_capacity_kw
                        or inputs.contract_capacities.get("regular", 0.0)
                    )
                    threshold = contract_kw * threshold_ratio
                    over_low = min(over, threshold)
                    over_high = max(0.0, over - threshold)
                    amount = base_rate.loc[idx] * over_low * rate_low
                    amount += base_rate.loc[idx] * over_high * rate_high
                    adjustment.loc[idx] += amount
                    details.append(
                        {
                            "period": idx,
                            "type": "over_contract",
                            "amount": float(amount),
                        }
                    )

    return adjustment, pd.DataFrame(details)


def _basic_fee_rate_for_label(
    plan_data: dict[str, Any],
    label: str,
    month_index: pd.Index,
    store: PlanStore,
) -> pd.Series | None:
    entries = plan_data.get("basic_fees", [])
    entry = next((e for e in entries if e.get("label") == label), None)
    if not entry:
        return None
    season_labels = _month_season_label(month_index, plan_data, store)
    rates = []
    for season_label in season_labels:
        if "summer" in entry or "non_summer" in entry:
            rate = (
                entry.get("summer")
                if season_label == "summer"
                else entry.get("non_summer")
            )
        else:
            rate = entry.get("cost")
        rates.append(float(rate) if rate is not None else 0.0)
    return pd.Series(rates, index=month_index)


def _basic_fee_from_formula(
    plan_data: dict[str, Any],
    inputs: BillingInputs,
    month_index: pd.Index,
    store: PlanStore,
    formula: dict[str, Any],
    detailed: bool = False,
) -> tuple[pd.Series, list[dict[str, Any]]]:
    season_labels = _month_season_label(month_index, plan_data, store)
    rates = {entry["label"]: entry for entry in plan_data.get("basic_fees", [])}
    monthly = pd.Series(0.0, index=month_index)
    details: list[dict[str, Any]] = []
    capacities = inputs.contract_capacities
    weekend_ratio = float(formula.get("weekend_ratio", 0.5))

    household_label = formula.get("household_label")
    if household_label:
        count = inputs.basic_fee_inputs.get(household_label, 1.0)
        entry = rates.get(household_label)
        if entry and entry.get("cost") is not None:
            monthly += float(entry["cost"]) * count
            if detailed:
                for ts in month_index:
                    details.append(
                        {
                            "period": ts,
                            "label": household_label,
                            "quantity": count,
                            "rate": float(entry["cost"]),
                            "cost": float(entry["cost"]) * count,
                        }
                    )

    def _season_rate(label: str, season_label: str) -> float:
        entry = rates.get(label, {})
        if "summer" in entry or "non_summer" in entry:
            rate = (
                entry.get("summer")
                if season_label == "summer"
                else entry.get("non_summer")
            )
            return float(rate) if rate is not None else 0.0
        rate = entry.get("cost")
        return float(rate) if rate is not None else 0.0

    for idx, season_label in enumerate(season_labels):
        if formula["type"] == "regular_only":
            rate = _season_rate(formula["regular_label"], season_label)
            quantity = capacities.get("regular", 0.0)
            cost = rate * quantity
            monthly.iloc[idx] += cost
            if detailed:
                details.append(
                    {
                        "period": month_index[idx],
                        "label": formula["regular_label"],
                        "quantity": quantity,
                        "rate": rate,
                        "cost": cost,
                    }
                )
            continue

        if formula["type"] == "two_stage":
            regular_rate = _season_rate(formula["regular_label"], season_label)
            non_summer_rate = _season_rate(formula["non_summer_label"], season_label)
            saturday_rate = _season_rate(formula["saturday_label"], season_label)
            regular = capacities.get("regular", 0.0)
            non_summer = capacities.get("non_summer", 0.0)
            saturday = capacities.get("saturday_semi_peak", 0.0)
            off_peak = capacities.get("off_peak", 0.0)

            weekend_base = (saturday + off_peak) - (
                regular + non_summer
            ) * weekend_ratio
            weekend_base = max(0.0, weekend_base)

            if season_label == "summer":
                cost_regular = regular_rate * regular
                cost_weekend = saturday_rate * weekend_base
                monthly.iloc[idx] += cost_regular + cost_weekend
                if detailed:
                    details.append(
                        {
                            "period": month_index[idx],
                            "label": formula["regular_label"],
                            "quantity": regular,
                            "rate": regular_rate,
                            "cost": cost_regular,
                        }
                    )
                    details.append(
                        {
                            "period": month_index[idx],
                            "label": formula["saturday_label"],
                            "quantity": weekend_base,
                            "rate": saturday_rate,
                            "cost": cost_weekend,
                        }
                    )
            else:
                cost_regular = regular_rate * regular
                cost_non_summer = non_summer_rate * non_summer
                cost_weekend = saturday_rate * weekend_base
                monthly.iloc[idx] += cost_regular + cost_non_summer + cost_weekend
                if detailed:
                    details.append(
                        {
                            "period": month_index[idx],
                            "label": formula["regular_label"],
                            "quantity": regular,
                            "rate": regular_rate,
                            "cost": cost_regular,
                        }
                    )
                    details.append(
                        {
                            "period": month_index[idx],
                            "label": formula["non_summer_label"],
                            "quantity": non_summer,
                            "rate": non_summer_rate,
                            "cost": cost_non_summer,
                        }
                    )
                    details.append(
                        {
                            "period": month_index[idx],
                            "label": formula["saturday_label"],
                            "quantity": weekend_base,
                            "rate": saturday_rate,
                            "cost": cost_weekend,
                        }
                    )
            continue

        if formula["type"] == "three_stage":
            regular_rate = _season_rate(formula["regular_label"], season_label)
            semi_rate = _season_rate(formula["semi_peak_label"], season_label)
            saturday_rate = _season_rate(formula["saturday_label"], season_label)
            regular = capacities.get("regular", 0.0)
            semi_peak = capacities.get("semi_peak", 0.0)
            saturday = capacities.get("saturday_semi_peak", 0.0)
            off_peak = capacities.get("off_peak", 0.0)

            weekend_base = (saturday + off_peak) - (regular + semi_peak) * weekend_ratio
            weekend_base = max(0.0, weekend_base)

            cost_regular = regular_rate * regular
            cost_semi = semi_rate * semi_peak
            cost_weekend = saturday_rate * weekend_base
            monthly.iloc[idx] += cost_regular + cost_semi + cost_weekend
            if detailed:
                details.append(
                    {
                        "period": month_index[idx],
                        "label": formula["regular_label"],
                        "quantity": regular,
                        "rate": regular_rate,
                        "cost": cost_regular,
                    }
                )
                details.append(
                    {
                        "period": month_index[idx],
                        "label": formula["semi_peak_label"],
                        "quantity": semi_peak,
                        "rate": semi_rate,
                        "cost": cost_semi,
                    }
                )
                details.append(
                    {
                        "period": month_index[idx],
                        "label": formula["saturday_label"],
                        "quantity": weekend_base,
                        "rate": saturday_rate,
                        "cost": cost_weekend,
                    }
                )

    return monthly, details


def _minimum_monthly_fee(plan_data: dict[str, Any]) -> float | None:
    rules = plan_data.get("billing_rules", {})
    value = rules.get("min_monthly_fee")
    if value is None:
        return None
    return float(value)


def _apply_minimum_usage(
    plan_data: dict[str, Any],
    store: PlanStore,
    usage: pd.Series,
    inputs: BillingInputs,
) -> pd.Series:
    rules = plan_data.get("billing_rules", {})
    ref = rules.get("minimum_usage_rules_ref")
    if not ref:
        return usage
    if (
        inputs.meter_phase is None
        or inputs.meter_voltage_v is None
        or inputs.meter_ampere is None
    ):
        return usage

    definitions = store.definitions()
    ruleset = definitions.get("minimum_usage_rules", {}).get(ref, [])
    if not ruleset:
        return usage

    target = None
    for item in ruleset:
        if item.get("phase") != inputs.meter_phase:
            continue
        if item.get("voltage_v") != inputs.meter_voltage_v:
            continue
        target = item
        break

    if not target:
        return usage

    ampere = float(inputs.meter_ampere)
    if "ampere_threshold" in target:
        threshold = target["ampere_threshold"]
        if ampere <= threshold:
            min_kwh = ampere * target["kwh_per_ampere"]
        else:
            min_kwh = ampere * target["kwh_per_ampere_over"]
    else:
        min_kwh = ampere * target["kwh_per_ampere"]

    if min_kwh <= 0:
        return usage

    billing_periods = _billing_period_index(usage.index, inputs.billing_cycle_months)
    adjusted = usage.copy()
    cycle_months = inputs.billing_cycle_months or 1
    for period, group in usage.groupby(billing_periods):
        total = group.sum()
        required = min_kwh * cycle_months
        if total >= required:
            continue
        if total > 0:
            factor = float(required / total)
            adjusted.loc[group.index] = group * factor
        else:
            adjusted.loc[group.index[0]] = required
    return adjusted


def _billing_period_index(
    index: pd.DatetimeIndex, cycle_months: int | None
) -> pd.PeriodIndex:
    if not cycle_months or cycle_months <= 1:
        return index.to_period("M")
    first = index.min()
    if first is pd.NaT:
        return index.to_period("M")
    start_year = first.year
    start_month = first.month
    months_since = (index.year - start_year) * 12 + (index.month - start_month)
    group = months_since // cycle_months
    base = pd.PeriodIndex(index, freq="M")
    start = base.min()
    return pd.PeriodIndex([start + int(g) * cycle_months for g in group], freq="M")


def _check_demand_resolution(demand: pd.Series) -> None:
    """Check demand data resolution and warn if coarser than 15 minutes.

    Taiwan Power Company calculates demand penalties based on 15-minute
    interval data. Using hourly or coarser data may underestimate peak demand
    and result in inaccurate penalty calculations.

    Args:
        demand: pandas Series with DatetimeIndex containing demand values in kW
    """
    if len(demand) < 2:
        return

    inferred_freq = demand.index.inferred_freq
    if inferred_freq is None:
        # Try to detect median interval
        intervals = demand.index.to_series().diff().dropna()
        if len(intervals) > 0:
            median_interval = intervals.median()
            minutes = median_interval.total_seconds() / 60
        else:
            return
    else:
        # Parse frequency string to get minutes
        freq_str = inferred_freq.upper()
        if freq_str.startswith("15T") or freq_str == "15MIN":
            return  # 15 minute data is ideal
        elif freq_str.startswith("30T") or freq_str == "30MIN":
            minutes = 30
        elif freq_str.startswith("H") or freq_str.startswith("1H"):
            minutes = 60
        elif freq_str.startswith("T"):
            # Parse minutes from T format (e.g., 5T, 10T)
            try:
                minutes = int(freq_str[1:]) if len(freq_str) > 1 else 1
            except ValueError:
                return
        else:
            return  # Unknown frequency, skip warning

    if minutes > 15:
        warnings.warn(
            f"Demand data resolution is approximately {int(minutes)} minutes, "
            f"which is coarser than the recommended 15-minute resolution. "
            f"Taiwan Power Company calculates demand penalties based on 15-minute "
            f"intervals. Using coarser data may underestimate peak demand and result "
            f"in inaccurate penalty calculations. "
            f"Consider using 'demand_adjustment_factor' parameter to apply a "
            f"conservative adjustment (e.g., 1.1-1.2 for hourly data).",
            UserWarning,
            stacklevel=3,
        )


def _compute_over_contract_kw(
    inputs: BillingInputs,
    context_df: pd.DataFrame,
    billing_periods: pd.PeriodIndex,
    oc_rule: dict[str, Any],
) -> pd.Series | None:
    if inputs.over_contract_kw is not None:
        return pd.Series(
            inputs.over_contract_kw, index=billing_periods.unique().to_timestamp()
        )
    demand = inputs.demand_kw
    if demand is None:
        return None
    if not isinstance(demand, pd.Series) or not isinstance(
        demand.index, pd.DatetimeIndex
    ):
        raise InvalidUsageInput("demand_kw must be a pandas.Series with DatetimeIndex")

    # Detect data resolution and warn if coarser than 15 minutes
    _check_demand_resolution(demand)

    # Apply adjustment factor if specified (default is 1.0)
    if inputs.demand_adjustment_factor != 1.0:
        demand = demand * inputs.demand_adjustment_factor

    categories = _demand_categories(context_df)
    demand = demand.reindex(context_df.index)
    combined = pd.DataFrame(
        {
            "demand": demand.values,
            "category": categories,
            "period": billing_periods,
        },
        index=context_df.index,
    )
    max_by_cat = (
        combined.groupby(["period", "category"], sort=False)["demand"].max().fillna(0.0)
    )
    results = {}
    for period, group in max_by_cat.groupby(level=0, sort=False):
        values = group.droplevel(0).to_dict()
        over = _calculate_over_contract_from_categories(
            values, inputs.contract_capacities, oc_rule
        )
        results[period.to_timestamp()] = over
    return pd.Series(results)


def _demand_categories(context_df: pd.DataFrame) -> pd.Series:
    categories = []
    for day_type, period in zip(context_df["day_type"], context_df["period"]):
        if str(day_type) == "saturday" and str(period) == "semi_peak":
            categories.append("saturday_semi_peak")
        else:
            categories.append(str(period))
    return pd.Series(categories, index=context_df.index)


def _calculate_over_contract_from_categories(
    max_demand: dict[str, float],
    capacities: dict[str, float],
    oc_rule: dict[str, Any],
) -> float:
    tier = oc_rule.get("tier", "two_stage")
    regular = capacities.get("regular", 0.0)
    non_summer = capacities.get("non_summer", 0.0)
    semi_peak = capacities.get("semi_peak", 0.0)
    saturday = capacities.get("saturday_semi_peak", 0.0)
    off_peak = capacities.get("off_peak", 0.0)

    if tier == "three_stage":
        peak_over = max(0.0, max_demand.get("peak", 0.0) - regular)
        semi_over = max(0.0, max_demand.get("semi_peak", 0.0) - (regular + semi_peak))
        saturday_over = max(
            0.0,
            max_demand.get("saturday_semi_peak", 0.0)
            - (regular + semi_peak + saturday),
        )
        off_over = max(
            0.0,
            max_demand.get("off_peak", 0.0)
            - (regular + semi_peak + saturday + off_peak),
        )
        semi_over = max(0.0, semi_over - peak_over)
        saturday_over = max(0.0, saturday_over - max(peak_over, semi_over))
        off_over = max(0.0, off_over - max(peak_over, semi_over, saturday_over))
        return max(peak_over, semi_over, saturday_over, off_over)

    peak_over = max(0.0, max_demand.get("peak", 0.0) - (regular + non_summer))
    saturday_over = max(
        0.0,
        max_demand.get("saturday_semi_peak", 0.0) - (regular + non_summer + saturday),
    )
    off_over = max(
        0.0,
        max_demand.get("off_peak", 0.0) - (regular + non_summer + saturday + off_peak),
    )
    saturday_over = max(0.0, saturday_over - peak_over)
    off_over = max(0.0, off_over - max(peak_over, saturday_over))
    return max(peak_over, saturday_over, off_over)


def _calculate_energy_costs(
    usage: pd.Series,
    context_df: pd.DataFrame,
    billing_periods: pd.PeriodIndex,
    tariff_plan: Any,
) -> pd.Series:
    rates = tariff_plan.rates
    if rates.tiered_rates:
        totals = {}
        for period, group in usage.groupby(billing_periods):
            if group.sum() == 0:
                totals[period.to_timestamp()] = 0.0
                continue
            season = context_df.loc[group.index, "season"].mode().iloc[0]
            season_label = season.value if hasattr(season, "value") else str(season)
            totals[period.to_timestamp()] = _tiered_total_cost(
                group.sum(),
                season_label,
                rates.tiered_rates,
            )
        return pd.Series(totals).sort_index()

    unit_costs = pd.Series(
        [
            rates.get_cost(season, period)
            for season, period in zip(context_df["season"], context_df["period"])
        ],
        index=usage.index,
    )
    interval_costs = usage * unit_costs
    totals = interval_costs.groupby(billing_periods).sum()
    if hasattr(totals, "index") and hasattr(totals.index, "to_timestamp"):
        totals.index = totals.index.to_timestamp()
    return totals


def _tiered_total_cost(
    total_usage_kwh: float,
    season_label: str,
    tiers: list[Any],
) -> float:
    if total_usage_kwh == 0:
        return 0.0
    sorted_tiers = sorted(tiers, key=lambda x: x.start_kwh)
    remaining_kwh = total_usage_kwh
    total_cost = 0.0
    last_limit_kwh = 0.0
    for tier in sorted_tiers:
        if remaining_kwh <= 0:
            break
        tier_limit_kwh = (
            (tier.end_kwh - last_limit_kwh) if tier.end_kwh < 999999 else float("inf")
        )
        usage_in_tier_kwh = min(remaining_kwh, tier_limit_kwh)
        unit_cost = (
            tier.summer_cost if season_label == "summer" else tier.non_summer_cost
        )
        total_cost += usage_in_tier_kwh * unit_cost
        remaining_kwh -= usage_in_tier_kwh
        last_limit_kwh = tier.end_kwh
    return total_cost


def _calculate_period_costs(
    usage: pd.Series,
    context_df: pd.DataFrame,
    billing_periods: pd.PeriodIndex,
    tariff_plan: Any,
) -> pd.DataFrame:
    rates = tariff_plan.rates
    records = []
    for period, group in usage.groupby(billing_periods):
        period_index = group.index
        month_context = context_df.loc[period_index]
        month_usage = group
        if rates.tiered_rates:
            season = month_context["season"].mode().iloc[0]
            season_label = season.value if hasattr(season, "value") else str(season)
            total_cost = _tiered_total_cost(
                month_usage.sum(), season_label, rates.tiered_rates
            )
            records.append(
                {
                    "period": period.to_timestamp(),
                    "season": season_label,
                    "period_type": "tiered",
                    "energy_cost": total_cost,
                }
            )
            continue

        unit_costs = pd.Series(
            [
                rates.get_cost(season, period_type)
                for season, period_type in zip(
                    month_context["season"], month_context["period"]
                )
            ],
            index=period_index,
        )
        costs = month_usage * unit_costs
        grouped = costs.groupby(
            [month_context["season"], month_context["period"]]
        ).sum()
        for (season, period_type), cost in grouped.items():
            season_label = season.value if hasattr(season, "value") else str(season)
            period_label = (
                period_type.value if hasattr(period_type, "value") else str(period_type)
            )
            records.append(
                {
                    "period": period.to_timestamp(),
                    "season": season_label,
                    "period_type": period_label,
                    "energy_cost": float(cost),
                }
            )

    return pd.DataFrame(records)


# ============================================================================
# Flexible Input Support (Non-Pandas Entry Points)
# ============================================================================


def _normalize_usage_to_series(
    usage: Any,
    start: Any = None,
    freq: str | None = None,
) -> pd.Series:
    """Convert various input formats to pandas.Series with DatetimeIndex.

    Args:
        usage: Input data - pd.Series, list of floats, or dict of timestamp:value
        start: Start date (required if usage is list), e.g. "2024-01-01"
        freq: Frequency string (e.g., "15min", "1h", "1D")

    Returns:
        pandas.Series with DatetimeIndex

    Raises:
        InvalidUsageInput: If input format is invalid or missing required params
    """
    if isinstance(usage, pd.Series):
        if not isinstance(usage.index, pd.DatetimeIndex):
            raise InvalidUsageInput("usage index must be a pandas.DatetimeIndex")
        return usage

    if isinstance(usage, list):
        if start is None:
            raise InvalidUsageInput(
                "start parameter is required when usage is a list. "
                "Example: start='2024-01-01'"
            )
        if freq is None:
            raise InvalidUsageInput(
                "freq parameter is required when usage is a list. "
                "Example: freq='1h' or freq='15min'"
            )
        index = pd.date_range(start=start, periods=len(usage), freq=freq)
        return pd.Series(usage, index=index)

    if isinstance(usage, dict):
        # Convert dict keys to timestamps
        try:
            index = pd.to_datetime(list(usage.keys()))
        except Exception as e:
            raise InvalidUsageInput(f"Cannot convert dict keys to datetime: {e}")
        return pd.Series(list(usage.values()), index=index)

    raise InvalidUsageInput(
        f"usage must be pd.Series, list, or dict, got {type(usage).__name__}"
    )


def calculate_bill_from_list(
    usage: list[float],
    plan_id: str,
    start: str | date,
    freq: str = "1h",
    inputs: BillingInputs | None = None,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
    strict: bool = False,
) -> pd.DataFrame:
    """Calculate bill from a list of usage values.

    This is a convenience function that avoids the need to create pandas objects.

    Args:
        usage: List of usage values in kWh
        plan_id: The plan identifier (flexible matching supported)
        start: Start date for the usage data (e.g., "2024-01-01")
        freq: Frequency of the data (e.g., "15min", "1h", "1D")
        inputs: Optional billing inputs
        calendar_instance: Optional calendar instance
        cache_dir: Optional cache directory for calendar
        api_timeout: API timeout for calendar
        strict: If True, raise errors on invalid/missing inputs

    Returns:
        DataFrame with billing breakdown

    Example:
        result = calculate_bill_from_list(
            usage=[1.0, 1.5, 2.0, 1.8, ...],
            plan_id="residential_simple_2_tier",
            start="2024-01-01",
            freq="1h",
        )
    """
    series = _normalize_usage_to_series(usage, start=start, freq=freq)
    return calculate_bill(
        series,
        plan_id,
        inputs=inputs,
        calendar_instance=calendar_instance,
        cache_dir=cache_dir,
        api_timeout=api_timeout,
        strict=strict,
    )


def calculate_bill_from_dict(
    usage: dict[str | date, float],
    plan_id: str,
    inputs: BillingInputs | None = None,
    calendar_instance: TaiwanCalendar | None = None,
    cache_dir: Path | None = None,
    api_timeout: int = 10,
    strict: bool = False,
) -> pd.DataFrame:
    """Calculate bill from a dictionary of timestamp -> usage values.

    This is a convenience function for irregularly-spaced or
    pre-aggregated usage data.

    Args:
        usage: Dictionary mapping timestamps to usage values in kWh.
                Timestamps can be strings or datetime objects.
        plan_id: The plan identifier (flexible matching supported)
        inputs: Optional billing inputs
        calendar_instance: Optional calendar instance
        cache_dir: Optional cache directory for calendar
        api_timeout: API timeout for calendar
        strict: If True, raise errors on invalid/missing inputs

    Returns:
        DataFrame with billing breakdown

    Example:
        result = calculate_bill_from_dict(
            usage={
                "2024-01-01 00:00": 1.0,
                "2024-01-01 01:00": 1.5,
                "2024-01-01 02:00": 2.0,
            },
            plan_id="residential_simple_2_tier",
        )
    """
    series = _normalize_usage_to_series(usage)
    return calculate_bill(
        series,
        plan_id,
        inputs=inputs,
        calendar_instance=calendar_instance,
        cache_dir=cache_dir,
        api_timeout=api_timeout,
        strict=strict,
    )
