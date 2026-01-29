"""Examples demonstrating billing cycle features.

This module shows practical usage of the three billing cycle types:
- MONTHLY: Monthly billing (1-month cycle)
- ODD_MONTH: Bimonthly billing with odd-month meter readings (1,3,5,7,9,11)
- EVEN_MONTH: Bimonthly billing with even-month meter readings (2,4,6,8,10,12)

Key features demonstrated:
- How billing periods are grouped
- How tier limits double for bimonthly billing
- Season boundary handling
- Year-crossing scenarios
- Comparing different billing cycles
"""

from __future__ import annotations

import pandas as pd

import tou_calculator as tou
from tou_calculator.models import BillingCycleType
from tou_calculator.tariff import _billing_period_group_index


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"{title:^70}")
    print(f"{'=' * 70}\n")


def print_subsection(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---\n")


def example_billing_cycle_types() -> None:
    """Demonstrate the three billing cycle types."""
    print_section("Billing Cycle Types")

    # Create sample usage data across multiple months
    dates = pd.to_datetime([
        "2025-02-15 10:00",
        "2025-02-15 14:00",
        "2025-03-15 10:00",
        "2025-03-15 14:00",
    ])
    usage = pd.Series([50.0, 50.0, 60.0, 60.0], index=dates)

    print("Usage data:")
    print(usage)
    print()

    # Show how different cycle types group the data
    for cycle_type in [
        BillingCycleType.MONTHLY,
        BillingCycleType.ODD_MONTH,
        BillingCycleType.EVEN_MONTH,
    ]:
        result = _billing_period_group_index(usage.index, cycle_type)
        print(f"{cycle_type.value} billing:")
        for date, period in zip(usage.index, result):
            print(f"  {date.strftime('%Y-%m-%d')} -> {period}")
        print()


def example_odd_month_billing() -> None:
    """Demonstrate ODD_MONTH billing cycle (Tai Power's default for residential)."""
    print_section("ODD_MONTH Billing Cycle")

    print("ODD_MONTH: Meters read in odd months (1, 3, 5, 7, 9, 11)")
    print("Billing periods:")
    print("  - (December, January) -> billed in January")
    print("  - (February, March) -> billed in March")
    print("  - (April, May) -> billed in May")
    print("  - (June, July) -> billed in July")
    print("  - (August, September) -> billed in September")
    print("  - (October, November) -> billed in November")

    # Create usage for February-March period
    dates = pd.to_datetime([
        "2025-02-01 00:00",
        "2025-02-15 00:00",
        "2025-03-01 00:00",
        "2025-03-15 00:00",
    ])
    usage = pd.Series([80.0, 70.0, 90.0, 85.0], index=dates)

    print_subsection("Usage for February-March period")
    print(usage)

    # Show grouping
    result = _billing_period_group_index(usage.index, BillingCycleType.ODD_MONTH)
    print(f"\nAll dates grouped to: {result.unique()[0]}")

    # Calculate bill using residential_non_tou (which uses 2-month billing)
    print_subsection("Bill calculation (residential_non_tou)")
    bill = tou.calculate_bill_simple(usage, "residential_non_tou")
    print(bill)


def example_even_month_billing() -> None:
    """Demonstrate EVEN_MONTH billing cycle."""
    print_section("EVEN_MONTH Billing Cycle")

    print("EVEN_MONTH: Meters read in even months (2, 4, 6, 8, 10, 12)")
    print("Billing periods:")
    print("  - (January, February) -> billed in February")
    print("  - (March, April) -> billed in April")
    print("  - (May, June) -> billed in June")
    print("  - (July, August) -> billed in August")
    print("  - (September, October) -> billed in October")
    print("  - (November, December) -> billed in December")

    # Create usage for January-February period
    dates = pd.to_datetime([
        "2025-01-01 00:00",
        "2025-01-15 00:00",
        "2025-02-01 00:00",
        "2025-02-15 00:00",
    ])
    usage = pd.Series([75.0, 80.0, 85.0, 90.0], index=dates)

    print_subsection("Usage for January-February period")
    print(usage)

    # Show grouping
    result = _billing_period_group_index(usage.index, BillingCycleType.EVEN_MONTH)
    print(f"\nAll dates grouped to: {result.unique()[0]}")


def example_year_crossing() -> None:
    """Demonstrate year-crossing scenarios for bimonthly billing."""
    print_section("Year-Crossing Scenarios")

    print_subsection("ODD_MONTH: December-January crossing")
    print("December usage is billed together with January of the NEXT year")

    dates = pd.to_datetime([
        "2024-12-15 00:00",
        "2025-01-15 00:00",
    ])
    usage = pd.Series([150.0, 160.0], index=dates)

    print(f"Usage:\n{usage}\n")

    result = _billing_period_group_index(usage.index, BillingCycleType.ODD_MONTH)
    print(f"Grouped to: {result.unique()[0]}")
    print("(December 2024 + January 2025 -> billed in January 2025)")

    print_subsection("EVEN_MONTH: December-January crossing")
    print("January usage is billed together with December of the PREVIOUS year")

    result = _billing_period_group_index(usage.index, BillingCycleType.EVEN_MONTH)
    print(f"Grouped to: {result.unique()[0]}")
    print("(December 2024 + January 2025 -> billed in December 2024)")


def example_tier_doubling() -> None:
    """Demonstrate how tier limits double for bimonthly billing."""
    print_section("Tier Limit Doubling for Bimonthly Billing")

    print("residential_non_tou plan:")
    print("  - Normal tier 1: 0-120 kWh @ 1.78 NT/kWh")
    print("  - Normal tier 2: 121-330 kWh @ 2.55/2.26 NT/kWh (summer/non-summer)")
    print("  - With 2-month billing: tier limits are DOUBLED")
    print("  - Bimonthly tier 1: 0-240 kWh @ 1.78 NT/kWh")
    print("  - Bimonthly tier 2: 241-660 kWh @ 2.55/2.26 NT/kWh")

    print_subsection("Example 1: 200 kWh usage (stays in tier 1)")
    dates = pd.to_datetime(["2025-02-01 00:00"])
    usage = pd.Series([200.0], index=dates)

    bill = tou.calculate_bill_simple(usage, "residential_non_tou")
    print(f"Usage: 200 kWh")
    print(f"Energy cost: {bill['energy_cost'].iloc[0]:.2f} NT")
    print(f"(200 kWh × 1.78 NT/kWh = {200 * 1.78:.2f} NT)")

    print_subsection("Example 2: 300 kWh usage (crosses into tier 2)")
    dates = pd.to_datetime(["2025-02-01 00:00"])
    usage = pd.Series([300.0], index=dates)

    bill = tou.calculate_bill_simple(usage, "residential_non_tou")
    print(f"Usage: 300 kWh")
    print(f"Energy cost: {bill['energy_cost'].iloc[0]:.2f} NT")
    print(f"Calculation:")
    print(f"  - First 240 kWh: 240 × 1.78 = {240 * 1.78:.2f} NT")
    print(f"  - Next 60 kWh: 60 × 2.26 = {60 * 2.26:.2f} NT")
    print(f"  - Total: {240 * 1.78 + 60 * 2.26:.2f} NT")


def example_season_boundary_handling() -> None:
    """Demonstrate how billing handles season boundaries."""
    print_section("Season Boundary Handling")

    print("Taiwan residential seasons:")
    print("  - Summer: June 1 - September 30")
    print("  - Non-summer: October 1 - May 31")

    print_subsection("February-March period (crosses season boundary)")

    # February is non-summer, March is summer
    dates = pd.to_datetime([
        "2025-02-15 00:00",  # Non-summer
        "2025-03-15 00:00",  # Summer
    ])
    usage = pd.Series([120.0, 130.0], index=dates)

    print(f"Usage:\n{usage}\n")

    bill = tou.calculate_bill_simple(usage, "residential_non_tou")
    print(f"Total usage: {usage.sum()} kWh")
    print(f"Energy cost: {bill['energy_cost'].iloc[0]:.2f} NT")
    print(f"\nNote: Feb-Mar period groups to March (summer)")
    print(f"Summer rates apply: 240 × 1.78 + 10 × 2.55 = {240 * 1.78 + 10 * 2.55:.2f} NT")

    print_subsection("October-November period (both non-summer)")

    dates = pd.to_datetime([
        "2025-10-15 00:00",  # Non-summer
        "2025-11-15 00:00",  # Non-summer
    ])
    usage = pd.Series([120.0, 130.0], index=dates)

    print(f"Usage:\n{usage}\n")

    bill = tou.calculate_bill_simple(usage, "residential_non_tou")
    print(f"Total usage: {usage.sum()} kWh")
    print(f"Energy cost: {bill['energy_cost'].iloc[0]:.2f} NT")
    print(f"\nNote: Oct-Nov period groups to November (non-summer)")
    print(f"Non-summer rates apply: 240 × 1.78 + 10 × 2.26 = {240 * 1.78 + 10 * 2.26:.2f} NT")


def example_monthly_vs_bimonthly_comparison() -> None:
    """Compare monthly vs bimonthly billing."""
    print_section("Monthly vs Bimonthly Billing Comparison")

    # Create same usage pattern for both plans
    dates = pd.to_datetime([
        "2025-02-15 00:00",
        "2025-03-15 00:00",
        "2025-04-15 00:00",
    ])
    usage = pd.Series([150.0, 150.0, 150.0], index=dates)

    print("Usage pattern: 150 kWh each in Feb, Mar, Apr")
    print()

    print_subsection("Monthly billing (residential_simple_2_tier)")
    print("This is a TOU (Time-of-Use) plan with monthly billing")

    bill_monthly = tou.calculate_bill_simple(usage, "residential_simple_2_tier")
    print(bill_monthly)

    print_subsection("Bimonthly billing (residential_non_tou)")
    print("This is a tiered plan with 2-month billing")
    print("Feb+Mar grouped together, Apr is start of next period")

    bill_bimonthly = tou.calculate_bill_simple(usage, "residential_non_tou")
    print(bill_bimonthly)


def example_practical_use_case() -> None:
    """Demonstrate a practical use case."""
    print_section("Practical Use Case: Analyzing Quarterly Bills")

    print("Scenario: A household wants to analyze their electricity costs")
    print("for Q1 2025 (January, February, March)")

    print_subsection("Step 1: Create sample usage data")

    # Simulate hourly data for Q1 2025
    # For simplicity, use daily averages
    dates_q1 = pd.date_range("2025-01-01", "2025-03-31", freq="D")
    # Simulate seasonal pattern: higher in Jan/Feb (heating), lower in Mar
    import numpy as np

    daily_usage = []
    for date in dates_q1:
        if date.month == 1:
            # January: ~10 kWh/day
            daily_usage.append(10.0 + np.random.uniform(-2, 2))
        elif date.month == 2:
            # February: ~9 kWh/day
            daily_usage.append(9.0 + np.random.uniform(-2, 2))
        else:
            # March: ~8 kWh/day
            daily_usage.append(8.0 + np.random.uniform(-2, 2))

    usage_q1 = pd.Series(daily_usage, index=dates_q1)

    print(f"Total Q1 usage: {usage_q1.sum():.1f} kWh")
    print(f"Daily average: {usage_q1.mean():.1f} kWh/day")

    print_subsection("Step 2: Calculate with bimonthly billing")

    # For ODD_MONTH billing: Jan alone (grouped with previous Dec), Feb+Mar together
    bill = tou.calculate_bill_simple(usage_q1, "residential_non_tou")

    print(f"\nBilling periods: {len(bill)}")
    print(bill)

    print_subsection("Step 3: Analyze cost components")

    breakdown = tou.calculate_bill_breakdown(usage_q1, "residential_non_tou")

    print("\nSummary:")
    print(breakdown["summary"])

    print("\nDetails by period:")
    print(breakdown["details"])


def main() -> None:
    """Run all examples."""
    example_billing_cycle_types()
    example_odd_month_billing()
    example_even_month_billing()
    example_year_crossing()
    example_tier_doubling()
    example_season_boundary_handling()
    example_monthly_vs_bimonthly_comparison()
    example_practical_use_case()


if __name__ == "__main__":
    main()
