"""Billing examples (simple vs advanced)."""

from __future__ import annotations

import pandas as pd

import taipower_tou as tou


def main() -> None:
    usage = pd.Series(
        [1.0, 2.0, 0.5],
        index=pd.to_datetime(
            ["2025-07-15 10:00", "2025-07-15 23:00", "2025-07-16 09:00"]
        ),
    )

    # Simple: just usage + plan id
    print("simple_bill:")
    print(tou.calculate_bill_simple(usage, "residential_simple_2_tier"))

    # Advanced: pass BillingInputs for contract capacity, PF, meter rules
    inputs = tou.BillingInputs(
        meter_phase="single",
        meter_voltage_v=110,
        meter_ampere=10,
    )
    print("advanced_bill:")
    print(tou.calculate_bill(usage, "residential_non_tou", inputs=inputs))

    # Advanced with demand series + contract capacities
    demand_index = pd.date_range("2025-07-15 00:00", periods=96, freq="15min")
    demand_kw = pd.Series(120.0, index=demand_index)
    inputs = tou.BillingInputs(
        contract_capacities={
            "regular": 100,
            "non_summer": 20,
            "saturday_semi_peak": 10,
            "off_peak": 10,
        },
        demand_kw=demand_kw,
        power_factor=82,
    )
    print("advanced_bill_demand:")
    print(tou.calculate_bill(usage, "high_voltage_2_tier", inputs=inputs))

    print("breakdown:")
    breakdown = tou.calculate_bill_breakdown(usage, "residential_simple_2_tier")
    print(breakdown["summary"])
    print(breakdown["details"])


if __name__ == "__main__":
    main()
