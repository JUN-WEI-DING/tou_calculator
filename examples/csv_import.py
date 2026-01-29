"""CSV Import Example - Import electricity usage from CSV file.

This example shows how to:
1. Read CSV file with timestamp and usage data
2. Parse and clean the data
3. Calculate electricity costs
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import tou_calculator as tou


def create_sample_csv(filename: str = "sample_usage.csv") -> None:
    """Create a sample CSV file for demonstration."""
    dates = pd.date_range("2025-07-01", periods=24 * 7, freq="h")  # 1 week
    data = {
        "timestamp": dates.strftime("%Y-%m-%d %H:%M"),
        "usage_kwh": [1.0 + (i % 3) * 0.5 for i in range(len(dates))],
    }
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"Created sample file: {filename}")


def import_from_csv_format_a(filename: str) -> pd.Series:
    """Import CSV Format A: timestamp and usage columns."""
    df = pd.read_csv(filename, encoding="utf-8-sig")

    # Ensure timestamp is datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Set timestamp as index
    df = df.set_index("timestamp")

    # Extract usage series
    usage = df["usage_kwh"]

    return usage


def import_from_csv_format_b(filename: str) -> pd.Series:
    """Import CSV Format B: Chinese column names."""
    df = pd.read_csv(filename, encoding="utf-8-sig")

    # Handle Chinese column names
    df["時間"] = pd.to_datetime(df["時間"])
    df = df.set_index("時間")

    usage = df["用電度數"]

    return usage


def import_from_csv_format_c(filename: str) -> pd.Series:
    """Import CSV Format C: Multiple columns with meter readings."""
    df = pd.read_csv(filename, encoding="utf-8-sig")

    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime")

    # Calculate usage from readings (current - previous)
    df["usage"] = df["reading"].diff().fillna(0)

    usage = df["usage"]

    return usage


def calculate_and_show(
    usage: pd.Series, plan_name: str = "residential_simple_2_tier"
) -> None:
    """Calculate and display electricity costs."""
    print("=" * 60)
    print("Electricity Cost Calculation")
    print("=" * 60)
    print()

    # Get date range
    start_date = usage.index.min()
    end_date = usage.index.max()

    # Get plan and calculate
    plan = tou.plan(plan_name)
    costs = plan.calculate_costs(usage)
    breakdown = plan.monthly_breakdown(usage, include_shares=True)

    # Display results
    print(f"Plan: {plan.name}")
    print(
        f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    )
    print()

    print(f"Total Usage: {usage.sum():.2f} kWh")
    print(f"Total Cost: {costs.sum():.2f} TWD")
    print(f"Average Rate: {costs.sum() / usage.sum():.2f} TWD/kWh")
    print()

    print("Monthly Breakdown:")
    print(breakdown.to_string(index=False))
    print()


def export_to_csv(
    usage: pd.Series,
    plan_id: str = "residential_simple_2_tier",
    filename: str = "result.csv",
) -> None:
    """Export hourly results to CSV file."""
    # Calculate hourly costs by multiplying usage by rate at each timepoint
    plan = tou.plan(plan_id)

    # Get the rate for each hour
    context_df = plan.profile.evaluate(usage.index)
    hourly_rates = []
    for _, row in context_df.iterrows():
        season = row["season"]
        period = row["period"]
        rate = plan.rates.get_cost(season, period)
        hourly_rates.append(rate)

    # Calculate hourly costs
    hourly_costs = usage.values * pd.Series(hourly_rates, index=usage.index).values

    result = pd.DataFrame(
        {
            "timestamp": usage.index.strftime("%Y-%m-%d %H:%M"),
            "usage_kwh": usage.values,
            "rate_twd_per_kwh": hourly_rates,
            "cost_twd": hourly_costs,
        }
    )
    result.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"Results exported to: {filename}")


# =============================================================================
# Main demonstration
# =============================================================================


def main() -> None:
    print("CSV Import Example")
    print("=" * 60)
    print()

    # Step 1: Create sample CSV
    print("Step 1: Creating sample CSV file...")
    create_sample_csv("sample_usage.csv")
    print()

    # Step 2: Import CSV
    print("Step 2: Importing CSV file...")
    usage = import_from_csv_format_a("sample_usage.csv")
    print(f"Imported {len(usage)} records")
    print(f"Date range: {usage.index.min()} to {usage.index.max()}")
    print()

    # Step 3: Calculate costs
    print("Step 3: Calculating electricity costs...")
    calculate_and_show(usage)
    print()

    # Step 4: Export results
    print("Step 4: Exporting results to CSV...")
    export_to_csv(usage, "residential_simple_2_tier", "result.csv")
    print()

    # Clean up sample files
    Path("sample_usage.csv").unlink(missing_ok=True)
    Path("result.csv").unlink(missing_ok=True)

    print("=" * 60)
    print("CSV Import Example Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
