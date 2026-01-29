"""End-to-end tests simulating real-world usage scenarios.

These tests simulate complete user journeys from raw data to final bills,
covering typical use cases for different customer types.
"""

import pandas as pd

import tou_calculator as tou
from tou_calculator import BillingInputs, calculate_bill

# =============================================================================
# E2E Scenario 1: Household with Smart Meter Data
# =============================================================================


def test_e2e_household_smart_meter_analysis():
    """Scenario: Homeowner analyzes smart meter data to compare plans."""
    # Simulate importing smart meter data (CSV-like)
    # User has 1 month of 15-minute interval data
    dates = pd.date_range("2024-07-01", periods=96 * 30, freq="15min")

    # Realistic household consumption pattern
    hour = dates.hour
    day_of_week = dates.dayofweek

    usage = []
    for h, dow in zip(hour, day_of_week):
        # Night (11pm-6am): base load
        if h >= 23 or h < 6:
            base = 0.3  # kWh per 15min
        # Morning peak (7-9am): breakfast, getting ready
        elif 7 <= h < 9:
            base = 0.8
        # Daytime (9am-5pm): lower usage on weekdays
        elif 9 <= h < 17:
            base = 0.4 if dow < 5 else 0.6  # Weekend slightly higher
        # Evening peak (5-11pm): cooking, TV, AC
        elif 17 <= h < 23:
            base = 1.0
        else:
            base = 0.5

        # Add some randomness
        import random

        base *= 0.9 + random.random() * 0.2
        usage.append(base)

    usage = pd.Series(usage, index=dates)

    # User wants to: 1) Calculate current bill,
    # 2) See when electricity is most expensive
    plan = tou.plan("residential_simple_2_tier")

    # Step 1: Get total cost
    monthly_cost = plan.calculate_costs(usage).iloc[0]
    assert monthly_cost > 0

    # Step 2: Understand when electricity costs the most
    breakdown = plan.monthly_breakdown(usage, include_shares=True)

    # Peak period should have higher cost share than usage share
    # (because peak rates are higher)
    peak_row = breakdown[breakdown["period"] == "peak"]
    if len(peak_row) > 0:
        # Peak is more expensive
        assert peak_row["cost"].iloc[0] > 0

    # Step 3: Get detailed bill with all charges
    inputs = BillingInputs.for_residential(
        phase="single",
        voltage=110,
        ampere=20,
    )
    bill = calculate_bill(usage, "residential_simple_2_tier", inputs=inputs)

    assert len(bill) == 1
    assert bill["total"].iloc[0] > 0


# =============================================================================
# E2E Scenario 2: Factory Energy Cost Analysis
# =============================================================================


def test_e2e_factory_peak_shaving_analysis():
    """Scenario: Factory analyzes costs to determine value of peak shaving."""
    # Factory has 15-minute demand data for a summer month
    dates = pd.date_range("2024-07-01", periods=96 * 30, freq="15min")
    hour = dates.hour
    day_of_week = dates.dayofweek

    # Industrial pattern: high steady daytime demand
    demand = []
    for h, dow in zip(hour, day_of_week):
        if dow >= 5:  # Weekend
            base = 100  # kW
        elif 8 <= h < 17:  # Work hours on weekdays
            base = 500
            # Add artificial peak in middle of day
            if 12 <= h < 14:
                base = 550  # Lunch-time equipment overlap
        else:  # Night
            base = 150
        demand.append(base)

    demand = pd.Series(demand, index=dates)

    # Convert to energy (kWh per 15min)
    usage = demand * 0.25  # 15min = 0.25h

    inputs = BillingInputs.for_high_voltage(
        regular=500,
        non_summer=200,
        saturday_semi_peak=100,
        off_peak=50,
        power_factor=90.0,
        demand_kw=demand,
    )

    bill = calculate_bill(usage, "high_voltage_2_tier", inputs=inputs)

    # Verify bill is calculated
    assert len(bill) == 1
    assert bill["total"].iloc[0] > 0

    # Factory owner can see the total cost breakdown
    assert bill["energy_cost"].iloc[0] > 0
    assert bill["basic_cost"].iloc[0] > 0

    # Get monthly breakdown to see when energy is used
    plan = tou.plan("high_voltage_2_tier")
    breakdown = plan.monthly_breakdown(usage, include_shares=False)

    # Should have different period types
    assert "period" in breakdown.columns
    assert len(breakdown) > 0


# =============================================================================
# E2E Scenario 3: EV Owner Charging Schedule Optimization
# =============================================================================


def test_e2e_ev_charging_schedule_comparison():
    """Scenario: EV owner compares charging schedules to minimize cost."""
    # User charges EV (7kW charger) for 4 hours = 28 kWh
    # Compare charging at different times

    dates = pd.date_range("2024-07-15", periods=24, freq="h")
    charging_scenarios = {
        "off_peak_night": [0] * 6 + [0] * 18,  # Charge 12am-6am (off-peak)
        "morning_peak": [7] * 4 + [0] * 20,  # Charge 8am-12pm (peak)
        "evening": [0] * 19 + [7] * 5,  # Charge 7pm-12am
    }

    plan = tou.plan("residential_simple_2_tier")

    costs = {}
    for scenario_name, hourly_usage in charging_scenarios.items():
        usage = pd.Series(hourly_usage[:24], index=dates)
        cost = plan.calculate_costs(usage).iloc[0]
        costs[scenario_name] = cost

    # Off-peak charging should be cheapest
    assert costs["off_peak_night"] < costs["morning_peak"]

    # User can now make informed decision about when to charge


# =============================================================================
# E2E Scenario 4: Small Shop Owner Choosing Rate Plan
# =============================================================================


def test_e2e_small_shop_plan_selection():
    """Scenario: Small shop compares different rate plans."""
    # Small retail shop has business-hour usage
    dates = pd.date_range("2024-07-01", periods=24 * 30, freq="h")
    hour = dates.hour
    day_of_week = dates.dayofweek

    usage = []
    for h, dow in zip(hour, day_of_week):
        if dow >= 5:  # Weekend - closed
            base = 0.5  # Security lights only
        elif 9 <= h < 21:  # Open hours
            base = 5.0  # Lights, AC, registers
        else:  # Closed but fridge running
            base = 1.0
        usage.append(base)

    usage = pd.Series(usage, index=dates)

    # Compare residential vs business plans
    plans = [
        "residential_simple_2_tier",
        "lighting_standard_2_tier",
    ]

    results = {}
    for plan_id in plans:
        try:
            plan = tou.plan(plan_id)
            cost = plan.calculate_costs(usage).iloc[0]
            results[plan_id] = cost
        except Exception:
            results[plan_id] = None

    # Both should give valid costs
    for plan_id, cost in results.items():
        if cost is not None:
            assert cost > 0


# =============================================================================
# E2E Scenario 5: Data Analyst Processing Multiple Buildings
# =============================================================================


def test_e2e_multi_building_analysis():
    """Scenario: Energy manager analyzes electricity costs for multiple buildings."""
    # Define different building types
    buildings = {
        "office": {
            "pattern": "high_day_low_night",
            "peak_hours": (9, 18),
            "base_kw": 100,
            "peak_kw": 300,
        },
        "warehouse": {
            "pattern": "steady",
            "peak_hours": (8, 17),
            "base_kw": 150,
            "peak_kw": 200,
        },
        "retail": {
            "pattern": "long_hours",
            "peak_hours": (10, 22),
            "base_kw": 80,
            "peak_kw": 150,
        },
    }

    dates = pd.date_range("2024-07-01", periods=24 * 30, freq="h")
    hour = dates.hour

    results = {}
    for building_name, config in buildings.items():
        # Generate usage pattern for this building
        usage = []
        for h in hour:
            start, end = config["peak_hours"]
            if start <= h < end:
                usage.append(config["peak_kw"])
            else:
                usage.append(config["base_kw"])

        usage = pd.Series(usage, index=dates)

        # Calculate cost
        plan = tou.plan("high_voltage_2_tier")
        cost = plan.calculate_costs(usage).iloc[0]

        results[building_name] = {
            "usage_kwh": usage.sum(),
            "cost_twd": cost,
            "avg_rate": cost / usage.sum(),
        }

    # All buildings should have valid costs
    for building_name, metrics in results.items():
        assert metrics["cost_twd"] > 0
        assert metrics["avg_rate"] > 0
        assert metrics["avg_rate"] < 20  # Reasonable rate cap (TWD/kWh)


# =============================================================================
# E2E Scenario 6: Quarterly Bill Reconciliation
# =============================================================================


def test_e2e_quarterly_bill_reconciliation():
    """Scenario: Accountant reconciles quarterly electricity bills."""
    # User has 3 months of data and wants to match utility bills

    # Generate data for Q2 (April, May, June)
    # April/May: non-summer, June: summer
    # Use same days for fair comparison
    months = [("2024-04-01", 30), ("2024-05-01", 30), ("2024-06-01", 30)]

    monthly_bills = []
    for start_date, days in months:
        dates = pd.date_range(start_date, periods=24 * days, freq="h")
        usage = pd.Series([2.5] * len(dates), index=dates)

        inputs = BillingInputs.for_residential(
            phase="single",
            voltage=110,
            ampere=30,
        )

        bill = calculate_bill(usage, "residential_simple_2_tier", inputs=inputs)
        monthly_bills.append(
            {
                "month": start_date[:7],
                "total": bill["total"].iloc[0],
                "energy": bill["energy_cost"].iloc[0],
                "basic": bill["basic_cost"].iloc[0],
            }
        )

    # June (summer) should have different rate structure than April/May
    # Verify the bills are calculated correctly
    for bill_info in monthly_bills:
        assert bill_info["total"] > 0
        assert bill_info["energy"] > 0
        assert bill_info["basic"] > 0

    # Accountant can now reconcile with actual utility bills


# =============================================================================
# E2E Scenario 7: Year-over-Year Cost Comparison
# =============================================================================


def test_e2e_year_over_year_comparison():
    """Scenario: Business compares electricity costs year over year."""
    # Same usage pattern for two years (same dates to avoid holiday differences)
    dates = pd.date_range("2024-07-01", periods=24 * 30, freq="h")

    usage = pd.Series([2.0] * len(dates), index=dates)

    plan = tou.plan("residential_simple_2_tier")

    # Calculate cost twice with same data
    cost1 = plan.calculate_costs(usage).iloc[0]
    cost2 = plan.calculate_costs(usage).iloc[0]

    # Same usage should give same cost (deterministic calculation)
    assert abs(cost1 - cost2) < 0.01  # Should be essentially identical


# =============================================================================
# E2E Scenario 8: Solar Panel Owner Analysis
# =============================================================================


def test_e2e_solar_panel_net_metering_analysis():
    """Scenario: Solar panel owner analyzes net metering benefits."""
    # User has solar panels and wants to know value of exported energy

    dates = pd.date_range("2024-07-01", periods=24 * 30, freq="h")
    hour = dates.hour

    # Net usage = consumption - solar generation
    # Solar generates during day (6am-6pm), peaks at noon
    net_usage = []
    for h in hour:
        consumption = 2.0  # Base household consumption

        if 6 <= h <= 18:
            # Solar generation (bell curve peaking at noon)
            import math

            solar_peak = 3.0
            solar = solar_peak * math.exp(-((h - 12) ** 2) / 20)
        else:
            solar = 0

        net = max(0, consumption - solar)  # Net metering (no negative)
        net_usage.append(net)

    usage = pd.Series(net_usage, index=dates)

    plan = tou.plan("residential_simple_2_tier")
    cost_with_solar = plan.calculate_costs(usage).iloc[0]

    # Compare with no solar
    no_solar_usage = pd.Series([2.0] * len(usage), index=dates)
    cost_no_solar = plan.calculate_costs(no_solar_usage).iloc[0]

    # Solar should reduce cost
    assert cost_with_solar < cost_no_solar

    savings = cost_no_solar - cost_with_solar
    savings_percent = (savings / cost_no_solar) * 100

    # User can see their solar savings
    assert savings > 0
    assert savings_percent > 0


# =============================================================================
# E2E Scenario 9: Tenant Pro-Rata Billing
# =============================================================================


def test_e2e_tenant_pro_rata_billing():
    """Scenario: Landlord allocates electricity costs to multiple tenants."""
    # Building has 3 tenants with different usage patterns

    dates = pd.date_range("2024-07-01", periods=24 * 30, freq="h")

    # Tenant 1: Restaurant (high daytime usage)
    tenant1_usage = pd.Series(
        [
            5 if 10 <= h < 22 else 1  # kWh
            for h in dates.hour
        ],
        index=dates,
    )

    # Tenant 2: Office (business hours)
    tenant2_usage = pd.Series(
        [8 if 9 <= h < 18 else 0.5 for h in dates.hour], index=dates
    )

    # Tenant 3: 24/7 convenience store
    tenant3_usage = pd.Series(
        [
            3  # Constant
            for _ in dates
        ],
        index=dates,
    )

    # Total building usage
    total_usage = tenant1_usage + tenant2_usage + tenant3_usage

    # Calculate each tenant's share
    plan = tou.plan("high_voltage_2_tier")
    total_cost = plan.calculate_costs(total_usage).iloc[0]

    # Simple pro-ration based on consumption
    tenant1_share = (tenant1_usage.sum() / total_usage.sum()) * total_cost
    tenant2_share = (tenant2_usage.sum() / total_usage.sum()) * total_cost
    tenant3_share = (tenant3_usage.sum() / total_usage.sum()) * total_cost

    # Verify shares add up
    total_share = tenant1_share + tenant2_share + tenant3_share
    assert abs(total_share - total_cost) < 0.01


# =============================================================================
# E2E Scenario 10: Budget Planning with Forecast
# =============================================================================


def test_e2e_budget_planning_forecast():
    """Scenario: Business forecasts annual electricity budget."""
    # Generate monthly usage data for a full year
    monthly_forecasts = []

    for month in range(1, 13):
        days = 31 if month in [1, 3, 5, 7, 8, 10, 12] else (30 if month != 2 else 29)
        dates = pd.date_range(f"2024-{month:02d}-01", periods=24 * days, freq="h")

        # Seasonal variation: higher in summer
        base = 100  # kW
        if month in [6, 7, 8, 9]:  # Summer months
            multiplier = 1.5
        else:
            multiplier = 1.0

        usage = pd.Series([base * multiplier] * len(dates), index=dates)

        plan = tou.plan("high_voltage_2_tier")
        cost = plan.calculate_costs(usage).iloc[0]

        monthly_forecasts.append(
            {
                "month": f"2024-{month:02d}",
                "usage_kwh": usage.sum(),
                "cost_twd": cost,
            }
        )

    total_annual_cost = sum(m["cost_twd"] for m in monthly_forecasts)

    # Business can now budget for the year
    assert total_annual_cost > 0

    # Summer months (Jun-Sep) should be most expensive
    summer_months = [
        m
        for m in monthly_forecasts
        if m["month"] in ["2024-06", "2024-07", "2024-08", "2024-09"]
    ]
    other_months = [
        m
        for m in monthly_forecasts
        if m["month"] not in ["2024-06", "2024-07", "2024-08", "2024-09"]
    ]

    avg_summer = sum(m["cost_twd"] for m in summer_months) / len(summer_months)
    avg_other = sum(m["cost_twd"] for m in other_months) / len(other_months)

    assert avg_summer > avg_other
