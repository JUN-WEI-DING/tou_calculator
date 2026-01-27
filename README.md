# Taiwan TOU Calculator

A specialized tool for calculating electricity costs based on Taiwan Power Company's (Taipower) Time-of-Use (TOU) tariffs.

This library encapsulates the complex rules of Taiwan's electricity pricing—including seasonal variations, holiday logic, and multi-stage rate schedules—into a simple, easy-to-use API.

## Installation

```bash
pip install tou-calculator
```

## Calculation Logic & Background (基本計算邏輯)

Taiwan's electricity pricing, especially for Time-of-Use (TOU) plans, is determined by three main factors. This calculator handles all of them efficiently:

1.  **Season (季節)**:
    - **Summer (夏月)**: June - September (Prices are generally higher).
    - **Non-Summer (非夏月)**: October - May.
    - *Note: High-voltage industrial users have a slightly longer summer period (mid-May to mid-Oct).*

2.  **Day Type (日類型)**:
    - **Weekdays**: Typically have Peak and Off-Peak hours.
    - **Weekends**: Often treated largely as Off-Peak.
    - **Holidays**: National holidays are treated as Off-Peak days (like Sundays). This library automatically fetches Taiwan's government holiday calendar to determine this correctly without manual input.

3.  **Time Period (時段)**:
    - **Peak (尖峰)**: Expensive hours (e.g., weekday afternoons).
    - **Off-Peak (離峰)**: Cheaper hours (nights, weekends).
    - **Semi-Peak (半尖峰)**: Intermediate rates for some industrial plans.

**Data Resolution Requirements (數據解析度要求)**

| Calculation Type | Recommended Resolution | Notes |
|------------------|------------------------|-------|
| Energy Cost (電能費) | Any resolution | Only total kWh per period matters |
| Demand Penalty (違約金) | **15 minutes** | Taipower uses 15-min average for contract capacity |
| Basic Fee (基本費) | N/A | Based on contract capacity, not usage |

**Critical for Industrial Users:**
Taipower calculates demand penalties based on **15-minute average demand** (台電詳細電價表：最高需量以15分鐘平均計算). Using hourly or coarser data for `demand_kw` may significantly underestimate peak demand and penalty charges. See Section 4 for detailed guidance.

**Why use this tool?**
Manually implementing these rules is error-prone because holidays change every year and peak hours differ by plan. `tou_calculator` automates this entire lookup process.

## API Quickstart (API 使用範例)

This guide covers the primary functions for querying plans, checking rates, and calculating costs.

### 1. Plan Information (查詢方案資訊)

**List Available Plans:**

```python
import tou_calculator as tou

print(tou.available_plans())
# 20 plans available:
# ['residential_non_tou', 'residential_simple_2_tier', 'residential_simple_3_tier',
#  'lighting_non_business_tiered', 'lighting_business_tiered',
#  'lighting_standard_2_tier', 'lighting_standard_3_tier',
#  'low_voltage_power', 'low_voltage_two_stage', 'low_voltage_three_stage', 'low_voltage_ev',
#  'high_voltage_power', 'high_voltage_two_stage', 'high_voltage_three_stage',
#  'high_voltage_batch', 'high_voltage_ev',
#  'extra_high_voltage_power', 'extra_high_voltage_two_stage',
#  'extra_high_voltage_three_stage', 'extra_high_voltage_batch']
```

**Get Plan Details:**
View the structure (seasons, day types, schedules) of a specific plan.

```python
plan = tou.plan("residential_simple_2_tier")
details = plan.describe()
print(f"Plan Name: {details['profile']['name']}")
```

### 2. Time & Rate Queries (查詢時間與費率)

**Check Holiday Status:**
The library automatically handles Taiwan's national holidays (e.g., New Year, Moon Festival).

```python
from datetime import datetime

# 2025-01-01 is a holiday
print(tou.is_holiday(datetime(2025, 1, 1)))  # True
# 2025-01-02 is a weekday
print(tou.is_holiday(datetime(2025, 1, 2)))  # False
```

**Check Period Type (Peak/Off-Peak):**

```python
dt = datetime(2025, 7, 15, 14, 0)
plan = "residential_simple_2_tier"

# Returns enum (e.g., PeriodType.PEAK)
print(tou.period_at(dt, plan))
```

**Get Full Time Context:**
If you need the Season and Day Type in addition to the Period:

```python
plan_obj = tou.plan(plan)
context = plan_obj.profile.engine.evaluate(
    pd.DatetimeIndex([dt])
)
print(f"Season: {context['season'].iloc[0]}")
print(f"Period: {context['period'].iloc[0]}")
```

**Get Pricing for a Timepoint:**

```python
# Check unit rate
plan_obj = tou.plan(plan)
ctx = plan_obj.pricing_context(dt)
print(f"Rate: {ctx['rate']} TWD/kWh")

# Calculate cost for specific usage amount
ctx_usage = plan_obj.pricing_context(dt, usage_kwh=10.0)
print(f"Cost: {ctx_usage['cost']} TWD")
```

### 3. Energy Cost Calculation (電能費用計算)

Calculate pure energy costs (Consumption × Rate) for time-series data.

```python
import pandas as pd

# Create sample usage data (index must be DatetimeIndex)
dates = pd.date_range("2025-07-15 14:00", periods=3, freq="h")
usage = pd.Series([1.5, 2.0, 1.8], index=dates)

# Get plan and calculate costs
plan_obj = tou.plan("residential_simple_2_tier")
costs = plan_obj.calculate_costs(usage)
print(f"Total Cost: {costs.sum():.2f}")

# Monthly breakdown with usage stats
report = plan_obj.monthly_breakdown(usage)
print(report)
# Returns DataFrame with: [month, season, period, usage_kwh, cost]
```

### 4. Advanced Bill Calculation (完整帳單計算)

For industrial or complex scenarios involving Basic Fees (基本費), Contract Capacities (契約容量), and Adjustments (Power Factor, etc.).

#### ⚠️ Important: Data Resolution Requirements (數據解析度要求)

**Taiwan Power Company's Official Standard (台電官方規定)**

According to Taipower's official tariff regulations (詳細電價表 第八章), contract capacity and demand penalties are calculated based on **15-minute average demand**:

> 「以雙方約定最高需量（**15分鐘平均**）為契約容量」

This means Taipower measures your highest power demand averaged over any 15-minute window during the billing period.

**Data Resolution Guidelines**

| Data Resolution | Accuracy | Risk | Recommendation |
|-----------------|----------|-------|----------------|
| **15 minutes** | ✅ Accurate | None | **Recommended** - Matches Taipower's official measurement |
| **30 minutes** | ⚠️ May underestimate | Up to 50% peak error | Use `demand_adjustment_factor=1.1-1.15` |
| **1 hour** | ⚠️ Underestimates likely | Up to 75% peak error | Use `demand_adjustment_factor=1.15-1.2` |
| **Daily** | ❌ Not reliable | Severe underestimation | Not recommended for penalty calculation |

**Why Resolution Matters: Peak Underestimation Example**

```
Actual 15-min demand pattern within one hour:
  14:00-14:15: 100 kW
  14:15-14:30: 200 kW  ← Taipower records: 200 kW peak
  14:30-14:45: 100 kW
  14:45-15:00: 100 kW

If using hourly averaged data:
  Hourly average = 125 kW
  Computed peak = 125 kW (37.5% UNDERESTIMATED!)

Penalty Impact (assuming 200 kW contract, 2x rate for over-contract):
  - Actual penalty: (200 - 200) × 2 = 0 kW (no penalty if contract=200)
  - With 200 kW contract and 230 kW actual peak: (230-200) × 2 = 60 kW × rate
  - With hourly data showing 200 kW: Penalty = 0 (WRONG - missed 30 kW overage!)
```

**Recommended Usage**

```python
from tou_calculator import calculate_bill, BillingInputs

# Best practice: Use 15-minute demand data
inputs = BillingInputs(
    contract_capacities={"regular": 200, "off_peak": 50},
    demand_kw=demand_15min,  # 15-minute interval data
    demand_adjustment_factor=1.0,  # No adjustment needed
)

# If only hourly data is available: apply conservative adjustment
inputs = BillingInputs(
    contract_capacities={"regular": 200, "off_peak": 50},
    demand_kw=demand_hourly,  # hourly data
    demand_adjustment_factor=1.15,  # 15% conservative adjustment
)
```

**The library will automatically warn** if detected resolution is coarser than 15 minutes.

**Calculate Total Bill:**

```python
from tou_calculator import calculate_bill, BillingInputs

# Configure billing parameters (contracts, power factor, etc.)
inputs = BillingInputs(
    contract_capacities={"regular": 200, "off_peak": 50},  # kW
    power_factor=95.0  # 95% (Resulting in discount)
)

# Calculate for High-Voltage Plan
# Returns DataFrame with columns: [energy_cost, basic_cost, surcharge, adjustment, total]
bill = calculate_bill(usage, "high_voltage_two_stage", inputs=inputs)
print(f"This Month's Bill: {bill['total'].iloc[0]:.0f} TWD")
```

**Detailed Bill Breakdown:**
If you need to know exactly how the bill was composed (e.g., how much was the Power Factor deduction):

```python
from tou_calculator import calculate_bill_breakdown

result = calculate_bill_breakdown(usage, "high_voltage_two_stage", inputs=inputs)

print("Summary:")
print(result["summary"])

print("\nLine Item Details:")
print(result["details"].head())  # Detailed period-by-period breakdown
print(result["adjustment_details"])  # Specific adjustments (e.g., PF discount amounts)
```

## Available Plans (可用方案)

All 20 Taipower plans are now supported. Plans are organized by category:

| Category | Plans |
|----------|-------|
| **Residential** | `residential_non_tou`, `residential_simple_2_tier`, `residential_simple_3_tier` |
| **Lighting** | `lighting_non_business_tiered`, `lighting_business_tiered`, `lighting_standard_2_tier`, `lighting_standard_3_tier` |
| **Low Voltage** | `low_voltage_power`, `low_voltage_two_stage`, `low_voltage_three_stage`, `low_voltage_ev` |
| **High Voltage** | `high_voltage_power`, `high_voltage_two_stage`, `high_voltage_three_stage`, `high_voltage_batch`, `high_voltage_ev` |
| **Extra High Voltage** | `extra_high_voltage_power`, `extra_high_voltage_two_stage`, `extra_high_voltage_three_stage`, `extra_high_voltage_batch` |

## Custom Plans (自定義費率)

You can also define custom calendars and rate schedules if the built-in Taipower plans don't fit your needs. (See `src/tou_calculator/custom.py` or the tests for advanced examples).
