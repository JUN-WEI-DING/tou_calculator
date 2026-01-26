"""Tariff rate loader for Taipower JSON data."""

from __future__ import annotations

import json
from importlib import resources
from typing import IO, Any

from tou_calculator.models import ConsumptionTier, PeriodType, SeasonType, TariffRate


class TariffJSONLoader:
    def __init__(
        self,
        filename: str = "plans.json",
        package: str = "tou_calculator.data",
    ) -> None:
        self._filename = filename
        self._package = package
        self._data: dict[str, Any] | None = None

    def _open_resource(self) -> IO[str]:
        if hasattr(resources, "files"):
            try:
                resource = resources.files(self._package).joinpath(self._filename)
                return resource.open("r", encoding="utf-8")
            except FileNotFoundError as exc:
                raise FileNotFoundError(
                    f"Tariff file not found in package: "
                    f"{self._package}/{self._filename}"
                ) from exc

        try:
            return resources.open_text(self._package, self._filename)
        except (ImportError, FileNotFoundError) as exc:
            raise FileNotFoundError(
                f"Tariff file not found in package (legacy): "
                f"{self._package}/{self._filename}"
            ) from exc
        except ModuleNotFoundError as exc:
            raise FileNotFoundError(
                f"Tariff package not found: {self._package}"
            ) from exc

    def load(self) -> dict[str, Any]:
        if self._data is None:
            with self._open_resource() as f:
                self._data = json.load(f)
        return self._data

    def _find_plan(self, plan_id: str) -> dict[str, Any]:
        data = self.load()
        for plan in data.get("plans", []):
            if plan.get("id") == plan_id:
                return plan
        raise KeyError(f"Plan not found: {plan_id}")

    def get_residential_simple_rate(self) -> TariffRate:
        try:
            section = self._find_plan("residential_simple_2_tier")["rates"]
            period_costs: dict[tuple[SeasonType | str, PeriodType | str], float] = {}

            for item in section:
                season = item.get("season")
                period = item.get("period")
                cost = item.get("cost")
                if season == "summer" and period == "peak":
                    period_costs[(SeasonType.SUMMER, PeriodType.PEAK)] = float(cost)
                elif season == "summer" and period == "off_peak":
                    period_costs[(SeasonType.SUMMER, PeriodType.OFF_PEAK)] = float(cost)
                elif season == "non_summer" and period == "peak":
                    period_costs[(SeasonType.NON_SUMMER, PeriodType.PEAK)] = float(cost)
                elif season == "non_summer" and period == "off_peak":
                    period_costs[(SeasonType.NON_SUMMER, PeriodType.OFF_PEAK)] = float(
                        cost
                    )

            return TariffRate(period_costs=period_costs)
        except (KeyError, TypeError):
            return TariffRate(period_costs={})

    def get_high_voltage_two_stage_rate(self) -> TariffRate:
        return TariffRate(period_costs={})

    def get_residential_non_tou_rate(self) -> TariffRate:
        try:
            section = self._find_plan("residential_non_tou")["tiers"]
            tiers = []

            for item in section:
                tier = ConsumptionTier(
                    start_kwh=float(item["min"]),
                    end_kwh=float(item["max"]) if item["max"] is not None else 999999.0,
                    summer_cost=float(item["summer"]),
                    non_summer_cost=float(item["non_summer"]),
                )
                tiers.append(tier)

            return TariffRate(tiered_rates=tiers)
        except KeyError:
            return TariffRate(tiered_rates=[])
