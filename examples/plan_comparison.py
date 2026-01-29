"""Plan Comparison Example - Compare electricity costs across different tariff plans.

This example shows how to:
1. Compare multiple plans for the same usage pattern
2. Find the cheapest plan for your usage
3. Visualize cost differences
"""

from __future__ import annotations

import pandas as pd

import tou_calculator as tou


def create_household_usage(summer_month: bool = True) -> pd.Series:
    """Create typical household usage pattern.

    Args:
        summer_month: True for July (summer), False for January (non-summer)
    """
    month = 7 if summer_month else 1
    days = 31 if month in [1, 3, 5, 7, 8, 10, 12] else 30

    dates = pd.date_range(f"2025-{month:02d}-01", periods=24 * days, freq="h")
    hour = dates.hour
    day_of_week = dates.dayofweek

    usage_values = []
    for h, dow in zip(hour, day_of_week):
        if dow >= 5:  # Weekend (Sat, Sun)
            usage_values.append(1.0)
        elif 9 <= h < 21:  # Weekday peak hours
            usage_values.append(2.5)
        else:  # Off-peak
            usage_values.append(0.8)

    return pd.Series(usage_values, index=dates)


def compare_residential_plans(usage: pd.Series) -> pd.DataFrame:
    """Compare all residential plans.

    Returns DataFrame with cost rankings.
    """
    residential_plans = [
        "residential_non_tou",
        "residential_simple_2_tier",
        "residential_simple_3_tier",
    ]

    results = []
    for plan_id in residential_plans:
        plan = tou.plan(plan_id)
        try:
            costs = plan.calculate_costs(usage)
            total_cost = costs.sum()
            total_kwh = usage.sum()
            avg_rate = total_cost / total_kwh

            results.append(
                {
                    "plan_id": plan_id,
                    "name": plan.name,
                    "total_cost": total_cost,
                    "total_kwh": total_kwh,
                    "avg_rate": avg_rate,
                    "rank": 0,  # Will be filled
                }
            )
        except Exception as e:
            print(f"Error calculating {plan_id}: {e}")

    df = pd.DataFrame(results)
    df = df.sort_values("total_cost")
    df["rank"] = range(1, len(df) + 1)
    df = df.reset_index(drop=True)

    return df


def compare_business_plans(usage: pd.Series) -> pd.DataFrame:
    """Compare business/lighting plans.

    Returns DataFrame with cost rankings.
    """
    business_plans = [
        "lighting_non_business_tiered",
        "lighting_business_tiered",
        "lighting_standard_2_tier",
        "lighting_standard_3_tier",
    ]

    results = []
    for plan_id in business_plans:
        plan = tou.plan(plan_id)
        try:
            costs = plan.calculate_costs(usage)
            total_cost = costs.sum()

            results.append(
                {
                    "plan_id": plan_id,
                    "name": plan.name,
                    "total_cost": total_cost,
                }
            )
        except Exception as e:
            print(f"Error calculating {plan_id}: {e}")

    df = pd.DataFrame(results)
    df = df.sort_values("total_cost")
    df["rank"] = range(1, len(df) + 1)
    df = df.reset_index(drop=True)

    return df


def print_comparison_table(df: pd.DataFrame, title: str = "Plan Comparison") -> None:
    """Pretty print comparison table."""
    print("=" * 80)
    print(title)
    print("=" * 80)
    print()

    for i, row in df.iterrows():
        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"  {i + 1}"
        print(f"{rank_emoji} #{row['rank']} {row['name']}")
        print(f"    Cost: {row['total_cost']:8.2f} TWD", end="")
        if "avg_rate" in row:
            print(f"  |  Avg: {row['avg_rate']:.2f} TWD/kWh")
        else:
            print()
        print()

    print("=" * 80)
    print()


def compare_summer_vs_winter() -> None:
    """Compare costs between summer and winter months."""
    print()
    print("Seasonal Cost Comparison")
    print("=" * 80)

    plans = ["residential_simple_2_tier", "residential_simple_3_tier"]

    print(f"{'Plan':<30} {'Summer (July)':>15} {'Winter (Jan)':>15} {'Difference':>15}")
    print("-" * 80)

    for plan_id in plans:
        plan = tou.plan(plan_id)

        # Summer
        summer_usage = create_household_usage(summer_month=True)
        summer_cost = plan.calculate_costs(summer_usage).sum()

        # Winter
        winter_usage = create_household_usage(summer_month=False)
        winter_cost = plan.calculate_costs(winter_usage).sum()

        diff = summer_cost - winter_cost
        diff_pct = (diff / winter_cost) * 100

        line = (
            f"{plan.name:<30} {summer_cost:10.2f} TWD  {winter_cost:10.2f} TWD  "
            f"{diff:+7.2f} ({diff_pct:+.1f}%)"
        )
        print(line)

    print("=" * 80)


def show_time_of_day_breakdown(usage: pd.Series, plan_id: str) -> None:
    """Show cost breakdown by time of day."""
    print()
    print("Time-of-Day Cost Breakdown")
    print("=" * 80)

    plan = tou.plan(plan_id)
    breakdown = plan.monthly_breakdown(usage, include_shares=True)

    print(f"{'Period':<15} {'Usage (kWh)':>15} {'Cost (TWD)':>15} {'Cost Share':>12}")
    print("-" * 80)

    for _, row in breakdown.iterrows():
        period_short = str(row["period"])[:12]
        cost_share = row["cost_share"] * 100
        # Break long line into multiple parts
        print(
            f"{period_short:<15} {row['usage_kwh']:13.2f}  {row['cost']:13.2f}  "
            f"{cost_share:8.1f}%"
        )

    print("=" * 80)


# =============================================================================
# Main demonstration
# =============================================================================


def main() -> None:
    print("Plan Comparison Example")
    print("=" * 80)
    print()

    # Create typical household usage (July - summer)
    usage = create_household_usage(summer_month=True)

    print("Sample Usage: July 2025 (31 days)")
    print(f"  Total: {usage.sum():.1f} kWh")
    print("  Pattern: Higher usage on weekday afternoons (2-5 PM)")
    print()

    # Compare residential plans
    print("1. RESIDENTIAL PLANS")
    print("-" * 80)
    df_residential = compare_residential_plans(usage)
    print_comparison_table(df_residential)

    # Show recommended plan
    cheapest = df_residential.iloc[0]
    print(f"💡 Recommendation: {cheapest['name']}")
    savings = df_residential["total_cost"].iloc[-1] - cheapest["total_cost"]
    print(f"    Saves {savings:.2f} TWD vs most expensive")
    print()

    # Time of day breakdown
    show_time_of_day_breakdown(usage, cheapest["plan_id"])

    # Seasonal comparison
    compare_summer_vs_winter()


if __name__ == "__main__":
    main()
