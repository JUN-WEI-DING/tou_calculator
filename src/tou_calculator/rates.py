"""Tariff rate loader for Taipower JSON data."""

from __future__ import annotations

import json
from importlib import resources
from typing import IO, Any


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

    def get_plan_data(self, plan_id: str) -> dict[str, Any]:
        """Get raw plan data by ID.

        Args:
            plan_id: The plan identifier

        Returns:
            The raw plan data dictionary

        Raises:
            KeyError: If plan_id is not found
        """
        return self._find_plan(plan_id)
