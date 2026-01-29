"""Quick Start Guide - 5 minutes to Taiwan TOU Calculator.

This example gets you started with the most common use cases.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

import tou_calculator as tou


def main():
    # =============================================================================
    # Example 1: Calculate cost for a single hour (最快上手：計算單小時電費)
    # =============================================================================

    print("=" * 60)
    print("Example 1: Single Hour Cost")
    print("=" * 60)

    # Create 1 hour of usage (1 kWh)
    dates = pd.date_range("2025-07-15 14:00", periods=1, freq="h")
    usage = pd.Series([1.0], index=dates)

    # Get plan and calculate
    plan = tou.plan("residential_simple_2_tier")  # or "簡易型二段式"
    cost = plan.calculate_costs(usage).iloc[0]

    print(f"Date: {dates[0]}")
    print("Usage: 1 kWh")
    print(f"Plan: {plan.name}")
    print(f"Season: {tou.period_at(dates[0], 'residential_simple_2_tier')}")
    print(f"Cost: {cost:.2f} TWD")
    print()

    # =============================================================================
    # Example 2: Calculate full day bill (計算整天電費)
    # =============================================================================

    print("=" * 60)
    print("Example 2: Full Day Bill")
    print("=" * 60)

    # Create 24 hours of usage
    dates = pd.date_range("2025-07-15", periods=24, freq="h")
    # Simulate typical household: higher in evening
    usage = pd.Series([1.0] * 24, index=dates)

    plan = tou.plan("residential_simple_2_tier")
    costs = plan.calculate_costs(usage)
    breakdown = plan.monthly_breakdown(usage)

    print(f"Total cost: {costs.iloc[0]:.2f} TWD")
    print(f"Total usage: {usage.sum():.1f} kWh")
    print(f"Average rate: {costs.iloc[0] / usage.sum():.2f} TWD/kWh")
    print()
    print("Period breakdown:")
    print(breakdown.to_string(index=False))
    print()

    # =============================================================================
    # Example 3: Check if a specific time is peak or off-peak (查詢尖峰/離峰)
    # =============================================================================

    print("=" * 60)
    print("Example 3: Check Rate Period")
    print("=" * 60)

    check_times = [
        datetime(2025, 7, 15, 14, 0),  # Weekday afternoon
        datetime(2025, 7, 15, 2, 0),  # Weekday night
        datetime(2025, 7, 13, 14, 0),  # Sunday afternoon
    ]

    for dt in check_times:
        period = tou.period_at(dt, "residential_simple_2_tier")
        ctx = tou.pricing_context(dt, "residential_simple_2_tier", usage=1.0)
        is_hol = tou.is_holiday(dt)
        day_type = "Holiday" if is_hol else "Weekday"
        print(
            f"{dt.strftime('%Y-%m-%d %H:%M')} | {day_type:7} | {period:10} | "
            f"{ctx['rate']:.2f} TWD/kWh"
        )
    print()

    # =============================================================================
    # Example 4: List all available plans (列出所有可用方案)
    # =============================================================================

    print("=" * 60)
    print("Example 4: Available Plans")
    print("=" * 60)

    plans = tou.available_plans()
    for i, plan_name in enumerate(plans[:10], 1):  # Show first 10
        print(f"{i}. {plan_name}")
    print(f"... and {len(plans) - 10} more")
    print()

    # =============================================================================
    # Example 5: Compare two plans (比較兩個方案)
    # =============================================================================

    print("=" * 60)
    print("Example 5: Plan Comparison")
    print("=" * 60)

    dates = pd.date_range("2025-07-01", periods=24 * 30, freq="h")  # July
    usage = pd.Series([2.0] * len(dates), index=dates)

    plans_to_compare = [
        "residential_simple_2_tier",
        "residential_simple_3_tier",
    ]

    print(f"Usage: {usage.sum():.0f} kWh (July 2025)")
    print()

    for plan_id in plans_to_compare:
        plan = tou.plan(plan_id)
        cost = plan.calculate_costs(usage).iloc[0]
        print(f"{plan_id:40s}: {cost:8.2f} TWD")

    print()
    print("=" * 60)
    print("Quick Start Complete!")
    print("More examples: csv_import.py, plan_comparison.py, household.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
