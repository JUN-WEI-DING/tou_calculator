"""Shared data structures for the TOU calculator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from enum import Enum
from typing import Any


class SeasonType(Enum):
    SUMMER = "summer"
    NON_SUMMER = "non_summer"


class PeriodType(Enum):
    PEAK = "peak"
    SEMI_PEAK = "semi_peak"
    OFF_PEAK = "off_peak"


@dataclass(frozen=True)
class TimeSlot:
    start: time
    end: time
    period_type: PeriodType | str


@dataclass(frozen=True)
class ConsumptionTier:
    start_kwh: float
    end_kwh: float
    summer_cost: float
    non_summer_cost: float


@dataclass(frozen=True)
class DaySchedule:
    slots: list[TimeSlot]


@dataclass
class TariffRate:
    period_costs: dict[tuple[SeasonType | str, PeriodType | str], float] = field(
        default_factory=dict
    )
    tiered_rates: list[ConsumptionTier] = field(default_factory=list)

    def rate_structure(self) -> str:
        has_periods = bool(self.period_costs)
        has_tiers = bool(self.tiered_rates)
        if has_periods and has_tiers:
            return "mixed"
        if has_tiers:
            return "tiered"
        if has_periods:
            return "tou"
        return "unknown"

    def get_cost(self, season: SeasonType | str, period: PeriodType | str) -> float:
        if (season, period) in self.period_costs:
            return self.period_costs[(season, period)]
        season_key = _label_value(season)
        period_key = _label_value(period)
        return self.period_costs.get((season_key, period_key), 0.0)

    def describe(self) -> dict[str, Any]:
        period_costs = [
            {
                "season": _label_value(season),
                "period": _label_value(period),
                "cost": cost,
            }
            for (season, period), cost in sorted(
                self.period_costs.items(),
                key=lambda item: (_label_value(item[0][0]), _label_value(item[0][1])),
            )
        ]
        tiered_rates = [
            {
                "start_kwh": tier.start_kwh,
                "end_kwh": tier.end_kwh,
                "summer_cost": tier.summer_cost,
                "non_summer_cost": tier.non_summer_cost,
            }
            for tier in self.tiered_rates
        ]
        return {
            "rate_structure": self.rate_structure(),
            "period_costs": period_costs,
            "tiered_rates": tiered_rates,
        }


def _label_value(value: Any) -> str:
    if isinstance(value, Enum):
        return value.value
    return str(value)
