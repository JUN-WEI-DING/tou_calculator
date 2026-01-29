"""Factory for creating tariff plans from JSON data."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from tou_calculator.calendar import TaiwanCalendar, taiwan_calendar
from tou_calculator.custom import (
    build_tariff_plan,
    build_tariff_profile,
    build_tariff_rate,
)
from tou_calculator.models import BillingCycleType
from tou_calculator.rates import TariffJSONLoader
from tou_calculator.tariff import TaiwanDayTypeStrategy, TaiwanSeasonStrategy

# Shared plan ID to Chinese name mapping
# Used by both PlanStore.resolve_plan() and available_plans()
_PLAN_NAME_MAP: dict[str, str] = {
    "residential_non_tou": "表燈非時間電價",
    "lighting_non_business_tiered": "表燈非時間-住宅非營業",
    "lighting_business_tiered": "表燈非時間-營業用",
    "residential_simple_2_tier": "簡易型二段式",
    "residential_simple_3_tier": "簡易型三段式",
    "lighting_standard_2_tier": "標準型二段式",
    "lighting_standard_3_tier": "標準型三段式",
    "low_voltage_power": "低壓電力非時間",
    "low_voltage_2_tier": "低壓電力二段式",
    "low_voltage_three_stage": "低壓電力三段式",
    "low_voltage_ev": "低壓電動車",
    "high_voltage_power": "高壓電力",
    "high_voltage_2_tier": "高壓電力二段式",
    "high_voltage_three_stage": "高壓電力三段式",
    "high_voltage_batch": "高壓批次生產",
    "high_voltage_ev": "高壓電動車",
    "extra_high_voltage_power": "特高壓電力",
    "extra_high_voltage_2_tier": "特高壓電力二段式",
    "extra_high_voltage_three_stage": "特高壓電力三段式",
    "extra_high_voltage_batch": "特高壓批次生產",
}

# Reverse mapping for Chinese name to plan ID lookup
_CHINESE_NAME_MAP: dict[str, str] = {v: k for k, v in _PLAN_NAME_MAP.items()}


@dataclass
class PlanRequirements:
    """Required and optional inputs for a tariff plan.

    Attributes:
        requires_contract_capacity: Whether the plan requires contract capacity
            input (typically for high_voltage and extra_high_voltage plans).
        requires_meter_spec: Whether the plan requires meter specifications
            (phase, voltage, ampere) for minimum usage calculation.
        valid_basic_fee_labels: Set of valid labels for basic_fee_inputs.
        uses_basic_fee_formula: Whether the plan uses a formula for basic fee
            calculation.
        formula_type: The type of formula ("two_stage", "three_stage", "regular_only").
    """

    requires_contract_capacity: bool
    requires_meter_spec: bool
    valid_basic_fee_labels: set[str]
    uses_basic_fee_formula: bool
    formula_type: str | None

    @classmethod
    def from_plan_data(cls, plan_data: dict[str, Any]) -> PlanRequirements:
        """Extract requirements from plan JSON data.

        Args:
            plan_data: The plan's JSON data dictionary.

        Returns:
            A PlanRequirements instance describing the plan's input requirements.
        """
        category = plan_data.get("category", "")
        basic_fees = plan_data.get("basic_fees", [])
        rules = plan_data.get("billing_rules", {})

        # High voltage and extra high voltage plans require contract capacity
        requires_contract_capacity = category in (
            "high_voltage",
            "extra_high_voltage",
        )

        # Plans with minimum usage rules require meter specifications
        requires_meter_spec = "minimum_usage_rules_ref" in rules

        # Extract all valid basic fee labels
        valid_basic_fee_labels = {
            fee.get("label", "") for fee in basic_fees if fee.get("label")
        }

        # Check if plan uses formula-based basic fee calculation
        uses_basic_fee_formula = "basic_fee_formula" in rules
        formula_type = rules.get("basic_fee_formula", {}).get("type")

        return cls(
            requires_contract_capacity=requires_contract_capacity,
            requires_meter_spec=requires_meter_spec,
            valid_basic_fee_labels=valid_basic_fee_labels,
            uses_basic_fee_formula=uses_basic_fee_formula,
            formula_type=formula_type,
        )


class PlanStore:
    """Centralized store for plan data from JSON."""

    def __init__(self, filename: str = "plans.json") -> None:
        self._loader = TariffJSONLoader(filename=filename)
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._data is None:
            self._data = self._loader.load()
        return self._data

    def definitions(self) -> dict[str, Any]:
        return self._load().get("definitions", {})

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        for plan in self._load().get("plans", []):
            if plan.get("id") == plan_id:
                return plan
        raise KeyError(f"Plan not found: {plan_id}")

    def resolve_plan(self, plan_id: str) -> dict[str, Any]:
        """Resolve plan ID with flexible matching.

        Supports:
        - Exact plan ID match (e.g., "residential_simple_2_tier")
        - Chinese name match (e.g., "簡易型二段式")
        - Partial keyword match (e.g., "二段式" matches any 2-tier plan)

        Args:
            plan_id: Plan identifier or Chinese name

        Returns:
            Copy of the plan data dictionary

        Raises:
            KeyError: If no matching plan is found
        """
        # Try exact match first
        try:
            return dict(self.get_plan(plan_id))
        except KeyError:
            pass

        # Try Chinese name mapping (using shared map)
        mapped_id = _CHINESE_NAME_MAP.get(plan_id.strip())
        if mapped_id:
            return dict(self.get_plan(mapped_id))

        # Try partial matching by checking plan names in JSON
        plan_id_lower = plan_id.lower()
        all_plans = self._load().get("plans", [])
        matches = []

        for plan in all_plans:
            pid = plan.get("id", "")
            name = plan.get("name", "")

            # Check if query is substring of ID or name
            if plan_id_lower in pid.lower() or plan_id_lower in name:
                matches.append((pid, plan))

        if len(matches) == 1:
            return dict(matches[0][1])

        if len(matches) > 1:
            match_ids = ", ".join(m[0] for m in matches)
            raise KeyError(
                f"Ambiguous plan name '{plan_id}'. "
                f"Multiple matches: {match_ids}. "
                f"Please use the exact plan ID."
            )

        raise KeyError(
            f"Plan not found: {plan_id}. "
            f"Use available_plans() to list all valid plan IDs."
        )

    @lru_cache(maxsize=1)
    def list_plan_ids(self) -> tuple[str, ...]:
        """Return tuple of all available plan IDs."""
        plans = self._load().get("plans", [])
        return tuple(p.get("id", "") for p in plans if p.get("id"))


class TariffFactory:
    """Factory for creating TariffPlan instances from JSON data."""

    def __init__(
        self,
        calendar: TaiwanCalendar | None = None,
        store: PlanStore | None = None,
    ) -> None:
        self._calendar = calendar or taiwan_calendar()
        self._store = store or PlanStore()

    def create_plan(
        self,
        plan_id: str,
        billing_cycle_type: BillingCycleType = BillingCycleType.MONTHLY,
    ) -> Any:
        """Create a TariffPlan from the given plan_id.

        Args:
            plan_id: The plan identifier or Chinese name (flexible matching supported)
            billing_cycle_type: Billing cycle type for tiered rate plans
                (MONTHLY, ODD_MONTH, EVEN_MONTH). Default is MONTHLY.

        Returns:
            A TariffPlan instance

        Raises:
            KeyError: If plan_id is not found
        """
        plan_data = self._store.resolve_plan(plan_id)
        return _build_tariff_plan_from_data(
            plan_data,
            self._store,
            self._calendar,
            billing_cycle_type=billing_cycle_type,
        )

    @classmethod
    def create(
        cls,
        plan_id: str,
        calendar: TaiwanCalendar | None = None,
        billing_cycle_type: BillingCycleType = BillingCycleType.MONTHLY,
    ) -> Any:
        """Convenience method to create a plan without instantiating factory."""
        return cls(calendar).create_plan(plan_id, billing_cycle_type)

    def list_plans(self) -> tuple[str, ...]:
        """Return all available plan IDs."""
        return self._store.list_plan_ids()


def _season_strategy(
    plan_data: dict[str, Any], store: PlanStore
) -> TaiwanSeasonStrategy:
    """Build season strategy from plan data."""
    strategy_name = plan_data.get("season_strategy", "seasons")
    definitions = store.definitions()
    seasons = definitions.get(strategy_name, [])
    if not seasons:
        return TaiwanSeasonStrategy((6, 1), (9, 30))
    summer = next((s for s in seasons if s.get("name") == "summer"), seasons[0])
    start_month, start_day = map(int, summer["start"].split("-"))
    end_month, end_day = map(int, summer["end"].split("-"))
    return TaiwanSeasonStrategy((start_month, start_day), (end_month, end_day))


def _normalize_schedules(schedules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize schedule data from JSON."""
    if not schedules:
        return []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in schedules:
        season = item["season"]
        day_type = item["day_type"]
        grouped.setdefault((season, day_type), []).append(
            {"start": item["start"], "end": item["end"], "period": item["period"]}
        )
    normalized = []
    for (season, day_type), slots in grouped.items():
        normalized.append({"season": season, "day_type": day_type, "slots": slots})
    return normalized


def _normalize_tiers(tiers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize tier data from JSON.

    Note: Tier scaling for bimonthly billing is handled in TariffPlan._calculate_tiered_costs()
    """
    if not tiers:
        return []

    normalized = []
    for item in tiers:
        start_kwh = float(item["min"])
        max_val = item.get("max")
        end_kwh = 999999.0 if max_val is None else float(max_val)

        normalized.append(
            {
                "start_kwh": start_kwh,
                "end_kwh": end_kwh,
                "summer_cost": item["summer"],
                "non_summer_cost": item["non_summer"],
            }
        )
    return normalized


def _build_tariff_plan_from_data(
    plan_data: dict[str, Any],
    store: PlanStore,
    calendar: TaiwanCalendar,
    billing_cycle_type: BillingCycleType = BillingCycleType.MONTHLY,
) -> Any:
    """Build a TariffPlan from raw plan data dictionary.

    This is the core factory function that creates a complete TariffPlan
    from JSON data, including profile and rates.
    """
    season_strategy = _season_strategy(plan_data, store)
    day_type_strategy = TaiwanDayTypeStrategy(calendar)

    schedules = _normalize_schedules(plan_data.get("schedules", []))
    if not schedules:
        schedules = [
            {
                "season": "summer",
                "day_type": "weekday",
                "slots": [{"start": "00:00", "end": "24:00", "period": "off_peak"}],
            }
        ]

    profile = build_tariff_profile(
        name=plan_data.get("name", plan_data.get("id", "Plan")),
        season_strategy=season_strategy,
        day_type_strategy=day_type_strategy,
        schedules=schedules,
        default_period="off_peak",
    )

    rates = plan_data.get("rates", [])
    tiered = _normalize_tiers(plan_data.get("tiers", []))

    rate = build_tariff_rate(
        period_costs=rates if rates else None,
        tiered_rates=tiered if tiered else None,
        season_strategy=season_strategy,
    )
    return build_tariff_plan(profile, rate, billing_cycle_type)
