"""Household Usage Example - Typical Taiwan household electricity cost calculation.

This example simulates a realistic household scenario with:
- Air conditioner usage in summer
- Refrigerator and appliances running 24/7
- Peak hours (evening) vs off-peak (night/morning)
- Weekend vs weekday patterns
"""

from __future__ import annotations

import pandas as pd

from tou_calculator import BillingInputs, calculate_bill


def create_realistic_household_usage(
    year: int = 2025,
    month: int = 7,
    include_ac: bool = True,
    ac_hours_start: int = 14,
    ac_hours_end: int = 23,
) -> pd.Series:
    """Create realistic household electricity usage pattern.

    Args:
        year: Year (default 2025)
        month: Month 1-12 (default 7 for July)
        include_ac: Whether to include AC usage
        ac_hours_start: AC start hour (default 14)
        ac_hours_end: AC end hour (default 23)

    Returns:
        pd.Series with hourly usage in kWh
    """
    days = 31 if month in [1, 3, 5, 7, 8, 10, 12] else 30
    dates = pd.date_range(f"{year}-{month:02d}-01", periods=24 * days, freq="h")

    usage_values = []
    for dt in dates:
        hour = dt.hour
        dow = dt.dayofweek
        is_summer = month in [6, 7, 8, 9]  # June-September
        is_weekend = dow >= 5

        # Base load (always running appliances)
        base_load = 0.15  # Refrigerator, WiFi router, standby devices

        # Morning routine (6-9 AM)
        if 6 <= hour < 9:
            morning_load = 0.8 if is_weekend else 1.2  # Shower pump, cooking
        else:
            morning_load = 0

        # Daytime low usage (9 AM - 5 PM)
        if 9 <= hour < 17:
            if is_weekend:
                daytime_load = 1.0
            else:
                daytime_load = 0.3  # Most people at work

        # Evening peak (5 PM - 11 PM)
        if 17 <= hour < 23:
            if is_weekend:
                evening_load = 1.5
            else:
                evening_load = 2.0

        # Night (11 PM - 6 AM)
        if hour >= 23 or hour < 6:
            night_load = 0.2

        # Air conditioning (summer only)
        ac_load = 0.0
        if include_ac and is_summer:
            if ac_hours_start <= hour < ac_hours_end:
                if is_weekend:
                    ac_load = 1.5  # Weekend AC use
                else:
                    ac_load = 2.5  # Weekday AC use (higher temp)

        # Total hourly usage
        total = (
            base_load
            + morning_load
            + daytime_load
            + evening_load
            + night_load
            + ac_load
        )
        usage_values.append(total)

    return pd.Series(usage_values, index=dates)


def calculate_monthly_bill(usage: pd.Series) -> pd.DataFrame:
    """Calculate complete monthly bill with all charges."""
    inputs = BillingInputs.for_residential(
        phase="single",
        voltage=110,
        ampere=20,
    )

    bill = calculate_bill(usage, "residential_simple_2_tier", inputs=inputs)
    return bill


def show_consumption_analysis(usage: pd.Series) -> None:
    """Analyze consumption patterns."""
    print("=" * 70)
    print("Consumption Analysis")
    print("=" * 70)

    # Total usage
    total_kwh = usage.sum()
    daily_avg = total_kwh / len(usage) * 24

    # Peak vs off-peak breakdown
    peak_hours = usage.index.hour.isin(range(9, 24))
    off_peak_hours = usage.index.hour.isin(range(0, 9))

    peak_usage = usage[peak_hours].sum()
    off_peak_usage = usage[off_peak_hours].sum()

    # Weekend vs weekday
    weekday_usage = usage[usage.index.dayofweek < 5].sum()
    weekend_usage = usage[usage.index.dayofweek >= 5].sum()

    print(f"Total Monthly Usage:      {total_kwh:8.2f} kWh")
    print(f"Daily Average:            {daily_avg:8.2f} kWh/day")
    print()
    peak_pct = peak_usage / total_kwh * 100
    off_peak_pct = off_peak_usage / total_kwh * 100
    print(f"Peak Hours (9AM-12AM):     {peak_usage:8.2f} kWh ({peak_pct:5.1f}%)")
    # Line too long - split into two
    print(f"Off-Peak (12AM-9AM):       {off_peak_usage:8.2f} kWh")
    print(f"                           ({off_peak_pct:5.1f}%)")
    print()
    print(f"Weekday Usage:            {weekday_usage:8.2f} kWh")
    print(f"Weekend Usage:            {weekend_usage:8.2f} kWh")
    print("=" * 70)
    print()


def show_appliance_breakdown(usage: pd.Series) -> None:
    """Estimate usage by appliance category."""
    print("=" * 70)
    print("Estimated Appliance Breakdown")
    print("=" * 70)

    # Rough estimation based on hourly patterns
    total_kwh = usage.sum()

    # Base load (24/7)
    base_load_kwh = 0.15 * len(usage)  # 0.15 kWh/hour * hours

    # AC usage (estimate)
    ac_hours = (usage.index.hour >= 14) & (usage.index.hour < 23)
    ac_hours_count = ac_hours.sum()
    ac_kwh = 2.0 * ac_hours_count  # Approx 2 kW when running

    # Other usage
    other_kwh = total_kwh - base_load_kwh - ac_kwh

    base_pct = base_load_kwh / total_kwh * 100
    print(f"Base Load (24/7):        {base_load_kwh:8.2f} kWh ({base_pct:5.1f}%)")
    print("  - Refrigerator, WiFi, standby")
    print()
    ac_pct = ac_kwh / total_kwh * 100
    print(f"Air Conditioning:         {ac_kwh:8.2f} kWh ({ac_pct:5.1f}%)")
    print(f"  - ~{ac_hours_count} hours at ~2 kW")
    print()
    other_pct = other_kwh / total_kwh * 100
    print(f"Other Appliances:        {other_kwh:8.2f} kWh ({other_pct:5.1f}%)")
    print("  - Cooking, shower, TV, lights")
    print("=" * 70)
    print()


def suggest_cost_saving_tips(usage: pd.Series, bill: pd.DataFrame) -> None:
    """Suggest cost-saving tips based on usage patterns."""
    print("=" * 70)
    print("Money-Saving Tips")
    print("=" * 70)

    # Calculate potential savings from shifting usage
    peak_hours = usage.index.hour.isin(range(9, 24))
    peak_usage = usage[peak_hours].sum()

    # If 20% of peak usage shifted to off-peak
    shifted_kwh = peak_usage * 0.2
    summer_peak_rate = 5.16
    summer_off_peak_rate = 2.06
    potential_savings = shifted_kwh * (summer_peak_rate - summer_off_peak_rate)

    print("💡 Shift 20% of peak usage to off-peak:")
    print(f"    Save ~{potential_savings:.2f} TWD/month")
    print("   - Run dishwasher/washing machine at night")
    print("   - Set AC timer to cool room before peak hours")
    print()

    # AC tips
    total_kwh = usage.sum()
    ac_kwh = 2.0 * ((usage.index.hour >= 14) & (usage.index.hour < 23)).sum()
    ac_pct = ac_kwh / total_kwh * 100

    print(f"💡 AC accounts for ~{ac_pct:.0f}% of your bill")
    print("   - Set AC to 26-28°C instead of 24-25°C")
    print("   - Use fan during cooler hours")
    print("   - Close curtains during hot hours")
    print()

    # Weekend vs weekday
    weekday_avg = usage[usage.index.dayofweek < 5].sum() / 30 / 24
    weekend_avg = usage[usage.index.dayofweek >= 5].sum() / 30 / 24

    if weekday_avg > weekend_avg:
        print("💡 Weekday usage is higher: Consider weekend activities")
        print(f"   - Weekday: {weekday_avg:.2f} kWh/hour avg")
        print(f"   - Weekend: {weekend_avg:.2f} kWh/hour avg")

    print("=" * 70)


# =============================================================================
# Main demonstration
# =============================================================================


def main() -> None:
    print("Household Electricity Cost Calculator")
    print("=" * 70)
    print()

    # Scenario 1: Summer month with AC
    print("Scenario: July 2025 (Summer) with Air Conditioning")
    print("-" * 70)

    usage_july = create_realistic_household_usage(year=2025, month=7, include_ac=True)
    show_consumption_analysis(usage_july)
    show_appliance_breakdown(usage_july)

    bill_july = calculate_monthly_bill(usage_july)

    print("Monthly Bill Breakdown:")
    print("-" * 70)
    print(f"Energy Cost:    {bill_july['energy_cost'].iloc[0]:8.2f} TWD")
    print(f"Basic Fee:      {bill_july['basic_cost'].iloc[0]:8.2f} TWD")
    print(f"Total Bill:      {bill_july['total'].iloc[0]:8.2f} TWD")
    print()

    suggest_cost_saving_tips(usage_july, bill_july)

    # Scenario 2: Winter month (no AC)
    print()
    print("Scenario: January 2025 (Winter) - No AC")
    print("-" * 70)

    usage_jan = create_realistic_household_usage(year=2025, month=1, include_ac=False)
    bill_jan = calculate_monthly_bill(usage_jan)

    total_july = bill_july["total"].iloc[0]
    total_jan = bill_jan["total"].iloc[0]

    print(f"Total Bill: {total_jan:8.2f} TWD")
    print()
    print(f"Summer vs Winter: July costs {total_july - total_jan:+.2f} TWD more")

    print()
    print("=" * 70)
    print("Example Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
