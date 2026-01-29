[![PyPI Version](https://img.shields.io/pypi/v/tou-calculator)](https://pypi.org/project/tou-calculator/)
[![Python](https://img.shields.io/pypi/pyversions/tou-calculator)](https://pypi.org/project/tou-calculator/)
[![License](https://img.shields.io/github/license/JUN-WEI-DING/tou_calculator)](https://github.com/JUN-WEI-DING/tou_calculator/blob/main/LICENSE)
[![Tests](https://github.com/JUN-WEI-DING/tou_calculator/actions/workflows/ci.yml/badge.svg)](https://github.com/JUN-WEI-DING/tou_calculator/actions)

# Taiwan TOU Calculator

A specialized tool for calculating electricity costs based on Taiwan Power Company's (Taipower) Time-of-Use (TOU) tariffs.

This library encapsulates the complex rules of Taiwan's electricity pricing—including seasonal variations, holiday logic, and multi-stage rate schedules—into a simple, easy-to-use API.

## Installation

```bash
# Basic installation
pip install tou-calculator

# With lunar calendar support (recommended for accurate holiday calculation)
pip install tou-calculator[lunar]

# Alternatively, using uv (faster)
uv pip install tou-calculator
uv add tou-calculator  # add to a project
```

## Quick Start Tutorial (快速入門教學)

This section teaches you how to use this library to calculate Taiwan electricity costs with simple examples. Whatever format your data is in, we can handle it!

這個章節用簡單的範例教你如何使用這個套件計算臺灣電費。不管你的資料是什麼格式，我們都能處理！

---

### Step 1: Prepare Your Data (準備你的用電資料)

This library requires two pieces of information: **Time** and **Usage (kWh)**. Time must be in datetime format, and usage is just a number.

這個套件需要「時間」和「用電度數」兩種資訊。時間必須是日期格式，用電度數就是數字。

#### Example A: Create Data Manually (範例 A：用 Python 手動建立資料)

```python
import pandas as pd
from datetime import datetime

# Method 1: Using list (simplest)
# 方法 1：用 list 建立（最簡單）
timestamps = [
    "2025-07-15 09:00",  # July 15, 2025, 9:00 AM
    "2025-07-15 10:00",
    "2025-07-15 11:00",
]
usage_kwh = [1.5, 2.3, 1.8]  # kWh used per hour

# Convert to pandas Series (required format)
# 轉換成 pandas Series（套件需要的格式）
dates = pd.to_datetime(timestamps)
usage_series = pd.Series(usage_kwh, index=dates)
print(usage_series)
# 2025-07-15 09:00:00    1.5
# 2025-07-15 10:00:00    2.3
# 2025-07-15 11:00:00    1.8
```

#### Example B: Read from CSV (範例 B：從 CSV 檔案讀取)

Assume you have an `electricity.csv` file:
假設你有一個 `electricity.csv` 檔案：

```csv
timestamp,usage
2025-07-15 09:00,1.5
2025-07-15 10:00,2.3
2025-07-15 11:00,1.8
```

```python
# Read CSV file
# 讀取 CSV 檔
df = pd.read_csv("electricity.csv")

# Ensure timestamp column is datetime format
# 確保時間欄位是日期格式
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Set time as index (important!)
# 將時間設為索引（重要！）
df = df.set_index("timestamp")

# Extract usage data
# 取出用電資料
usage_series = df["usage"]
```

#### Example C: Read from Excel (範例 C：從 Excel 檔案讀取)

```python
# Read Excel file
# 讀取 Excel 檔
df = pd.read_excel("electricity.xlsx", sheet_name="July")

# Assuming column names are "時間" and "用電度數"
# 假設欄位名稱是 "時間" 和 "用電度數"
df["時間"] = pd.to_datetime(df["時間"])
df = df.set_index("時間")

usage_series = df["用電度數"]
```

#### Example D: Handle Different Data Formats (範例 D：處理不同的資料格式)

```python
import numpy as np

# numpy array → convert to Series
# numpy array → 轉成 Series
usage_array = np.array([1.5, 2.3, 1.8])
dates = pd.date_range("2025-07-15 09:00", periods=3, freq="h")
usage_series = pd.Series(usage_array, index=dates)

# DataFrame → use index directly
# DataFrame → 直接使用索引
df = pd.DataFrame({
    "時間": pd.date_range("2025-07-15", periods=24, freq="h"),
    "用電": np.random.rand(24) * 5  # random usage data
})
df = df.set_index("時間")
usage_series = df["用電"]
```

---

### Step 1.5: No-Pandas Convenience Functions (無需 Pandas 的便利函式)

**Don't want to deal with pandas?** We provide convenience functions that accept plain Python lists or dictionaries!
**不想處理 pandas？** 我們提供接受純 Python list 或 dict 的便利函式！

#### Using List (使用 list)

```python
import tou_calculator as tou

# For regularly-spaced data, just pass a list of values
# 對於固定間隔的資料，只需傳入數值列表
result = tou.calculate_bill_from_list(
    usage=[1.5, 2.3, 1.8, 2.0, 1.6],  # kWh values
    plan_id="簡易型二段式",              # Flexible name matching
    start="2025-07-15 09:00",          # Start datetime
    freq="1h",                          # Frequency: 15min, 1h, 1D, etc.
)
print(f"Total: {result['total'].iloc[0]:.2f} TWD")
```

#### Using Dictionary (使用 dict)

```python
# For irregularly-spaced data, use a dictionary
# 對於不規則間隔的資料，使用字典
result = tou.calculate_bill_from_dict(
    usage={
        "2025-07-15 09:00": 1.5,
        "2025-07-15 10:00": 2.3,
        "2025-07-15 11:00": 1.8,
        "2025-07-15 14:30": 2.0,  # Irregular interval allowed
    },
    plan_id="residential_simple_2_tier",
)
print(f"Total: {result['total'].iloc[0]:.2f} TWD")
```

#### Comparison (對比)

| Method | Best For | Example Input |
|--------|----------|---------------|
| `calculate_bill` | pandas users, large datasets | `pd.Series` with DatetimeIndex |
| `calculate_bill_from_list` | Regular intervals (hourly, daily) | `[1.0, 1.5, 2.0]` + start + freq |
| `calculate_bill_from_dict` | Irregular intervals | `{"2025-07-15 09:00": 1.0, ...}` |

---

### Step 2: Choose Your Tariff Plan (選擇你的電價方案)

Taipower has many plans. Let's see what's available:
臺電有很多種方案，先看看有哪些：

```python
import tou_calculator as tou

# List all available plan IDs
# 列出所有可用的 plan ID
print(tou.available_plans())
# ['residential_non_tou', 'lighting_non_business_tiered',
#  'residential_simple_2_tier', 'residential_simple_3_tier', ...]
```

Common plans:
常見的方案：

| Category | 分類 | Plan ID |
|----------|------|---------|
| Residential | 家庭用電 | `residential_simple_2_tier` |
| Residential | 家庭用電 | `residential_simple_3_tier` |
| Low Voltage | 低壓用電 | `low_voltage_2_tier` |
| High Voltage | 高壓用電 | `high_voltage_2_tier` |
| High Voltage | 高壓用電 | `high_voltage_three_stage` |

---

### Step 3: Check Rate Period (判斷費率時段)

Before calculating costs, you might want to know what rate period applies at a specific time.  
在計算電費之前，你可能想知道某個時間點屬於哪個費率時段。

```python
from datetime import datetime

# Check period type at a specific time
# 查詢特定時間的時段型別
dt = datetime(2025, 7, 15, 14, 0)  # July 15, 2025, 2:00 PM (summer weekday afternoon)

period = tou.period_at(dt, "residential_simple_2_tier")
print(f"Period: {period}")  # Output: PeriodType.PEAK (尖峰)

# Check if it's a holiday
# 檢查是否為國定假日
is_holiday = tou.is_holiday(dt)
print(f"Is Holiday: {is_holiday}")  # Output: False

# Get pricing context (rate + more details)
# 取得費率資訊（費率 + 更多細節）
ctx = tou.pricing_context(dt, "residential_simple_2_tier")
print(f"Season: {ctx['season']}")   # summer (夏月)
print(f"Period: {ctx['period']}")   # peak (尖峰)
print(f"Rate: {ctx['rate']} TWD/kWh")  # 5.16 TWD/kWh
```

**Common Period Types (常見時段型別):**

| Period Type | 時段 | Description |
|-------------|------|-------------|
| `PEAK` | 尖峰 | Highest rate, usually weekday afternoons in summer |
| `SEMIPPEAK` | 半尖峰 | Medium rate, usually Saturday or weekday evenings |
| `OFF_PEAK` | 離峰 | Lowest rate, nights, Sundays, and holidays |

---

### Step 4: Calculate Costs (計算電費)

#### Basic Calculation: Energy Cost Only (基礎計算：只算電能費)

```python
# Get plan object
# 取得方案物件
plan = tou.plan("residential_simple_2_tier")

# Calculate costs (returns monthly aggregated costs)
# 計算電費（返回按月匯總的電費）
costs = plan.calculate_costs(usage_series)

# View results
# 看結果
print(f"Total Cost: {costs.iloc[0]:.2f} TWD")  # 總電費
print(costs)
# 2025-07-01    28.90
# Name: cost, dtype: float64
```

**Note:** `calculate_costs()` returns monthly aggregated costs by default.
**說明：** `calculate_costs()` 預設返回按月匯總的電費。

#### Advanced Calculation: With Basic Fee and Penalty (進階計算：包含基本費和違約金)

For industrial users or those with contract capacity:
適合工業使用者或有契約容量的使用者：

```python
from tou_calculator import calculate_bill, BillingInputs

# Set contract capacity (in kW)
# 設定契約容量（以 kW 為單位）
inputs = BillingInputs(
    contract_capacities={"regular": 100},  # 100 kW contract
    power_factor=90.0,  # 90% power factor
)

# Calculate full bill
# 計算完整帳單
bill = calculate_bill(usage_series, "high_voltage_2_tier", inputs=inputs)

print(bill)
# Energy Cost | Basic Fee | Penalty | PF Adjustment | Total
# 電能費      | 基本費    | 違約金  | 功率因數調整     | 總計
```

---

### Step 5: View Detailed Report (檢視詳細報表)

```python
# View monthly statistics
# 檢視每月統計
report = plan.monthly_breakdown(usage_series)
print(report)
#         month  season period  usage_kwh     cost
# 0 2025-07-01  summer   peak        5.6  28.90
```

---

### Step 6: Export Results (匯出結果)

```python
# Save results to CSV
# 把結果存成 CSV
result_df = pd.DataFrame({
    "Usage_kWh": usage_series,  # 用電度數
    "Cost_TWD": costs,           # 電費
})
result_df.to_csv("電費計算結果.csv", encoding="utf-8-sig")

# Or save to Excel
# 或存成 Excel
result_df.to_excel("電費計算結果.xlsx")
```

---

### Complete Example: End-to-End (完整範例：從頭到尾)

```python
import pandas as pd
import tou_calculator as tou

# 1. Load your usage data
# 1. 讀取你的用電資料
df = pd.read_csv("my_usage.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.set_index("timestamp")

# 2. Get tariff plan
# 2. 取得電價方案
plan = tou.plan("residential_simple_2_tier")

# 3. Calculate costs
# 3. 計算電費
costs = plan.calculate_costs(df["usage"])

# 4. Print results
# 4. 印出結果
print(f"Total Cost: {costs.sum():.2f} TWD")
print(f"總電費: {costs.sum():.2f} 元")
print(f"Total Usage: {df['usage'].sum():.2f} kWh")
print(f"總用電: {df['usage'].sum():.2f} 度")
print(f"Average per kWh: {costs.sum() / df['usage'].sum():.2f} TWD")
print(f"平均每度: {costs.sum() / df['usage'].sum():.2f} 元")
```

---

## Calculation Logic & Background (基本計算邏輯)

This section explains how Taiwan Power Company (Taipower) calculates electricity bills. Understanding this helps you verify the results and optimize your electricity usage.

### Quick Formula (電費計算公式)

```
總電費 = 電能費 + 基本費 + 違約金 ± 功率因數調整 + 其他調整

Total Bill = Energy Cost + Basic Fee + Penalty ± PF Adjustment + Others
```

---

### 1. Energy Cost (電能費) - Consumption × Rate

**The electricity you use during different time periods is charged at different rates.**

```
電能費 = Σ(各時段用電度數 × 該時段費率)

Energy Cost = Σ(Usage_kWh × Rate) for each time period
```

**How it works:**

| Component | Description | Example |
|-----------|-------------|---------|
| **用電度數** | Your actual electricity consumption | 150 kWh in peak hours |
| **時段費率** | Different rate for each time period | $5.16/kWh for summer peak |
| **計算** | Multiply and sum across all periods | 150 × 5.16 = $774 |

**Rate varies by:**

| Factor | Options | Impact on Rate |
|--------|---------|----------------|
| **季節 Season** | 夏月 Summer (6-9月) / 非夏月 Non-Summer | Summer rates ≈ 20-40% higher |
| **日期 Day Type** | 週日+國定假日 Sunday+Holidays / 週六 Saturday / 平日 Weekday | Holidays get off-peak rates |
| **時段 Time Period** | 尖峰 Peak / 半尖峰 Semi-Peak / 離峰 Off-Peak | Peak most expensive, off-peak cheapest |

---

### 2. Basic Fee (基本費) - Contract Capacity × Unit Price

**A fixed monthly fee based on your contracted power capacity.**

```
基本費 = 契約容量(kW) × 單價

Basic Fee = Contract Capacity(kW) × Unit Rate
```

| Fee Type | Description | Who Pays This |
|----------|-------------|---------------|
| **經常契約** | Regular contract capacity (year-round) | All contract users |
| **非夏月契約** | Additional non-summer capacity | High-voltage users |
| **半尖峰契約** | Semi-peak capacity | 3-stage TOU users |
| **週六半尖峰契約** | Saturday semi-peak capacity | 2/3-stage TOU users |
| **離峰契約** | Off-peak capacity | 2/3-stage TOU users |

---

### 3. Demand Penalty (違約金) - Exceeding Contract Capacity

**If your peak demand exceeds your contract capacity, you pay a penalty.**

```
最高需量 = 當月內任意15分鐘平均功率的最大值
Peak Demand = Maximum 15-minute average power during the month

超約容量 = 最高需量 - 契約容量
Over-contract = Peak Demand - Contract Capacity

違約金 = 超約容量 × 基本費單價 × 罰款倍率
Penalty = Over-contract × Basic Fee Rate × Penalty Multiplier
```

**Penalty Rates:**

| Over-contract Amount | Penalty Rate |
|---------------------|--------------|
| Within 10% of contract | **2×** basic fee rate |
| Exceeds 10% of contract | **3×** basic fee rate (for the excess portion) |

**Example:**
- Contract: 200 kW
- Actual peak: 230 kW
- Over-contract: 30 kW (15% over)
- Penalty calculation:
  - First 20 kW (10%): 20 × Rate × 2
  - Remaining 10 kW: 10 × Rate × 3

---

### 4. Power Factor Adjustment (功率因數調整)

**Power factor measures how efficiently you use electricity. Taipower rewards high PF and penalizes low PF.**

```
功率因數調整 = 基本費 × (基準功率因數% - 實際功率因數%) × 0.1%

PF Adjustment = Basic Fee × (Base PF% - Actual PF%) × 0.1%
```

| Power Factor | Result | Example |
|--------------|--------|---------|
| **> 80%** (base) | Discount | 95% PF → 1.5% discount on basic fee |
| **< 80%** (base) | Surcharge | 75% PF → 0.5% surcharge on basic fee |
| **Max discount** | Up to 95% PF | Max discount = (95-80) × 0.1% = 1.5% |

---

### Complete Bill Example (完整帳單範例)

**Scenario:** High-voltage factory in July (summer)

| Item | Calculation | Amount (TWD) |
|------|-------------|--------------|
| **Energy Cost** | Peak: 10,000 kWh × $5.16 | 51,600 |
| | Off-peak: 20,000 kWh × $2.06 | 41,200 |
| | **Subtotal** | **92,800** |
| **Basic Fee** | 200 kW × $236.20 | 47,240 |
| **Penalty** | (230-200) kW × $236.20 × 2 | 14,172 |
| **PF Discount** | -47,240 × 1.5% | -709 |
| **Total** | | **153,503** |

---

### Data Resolution Requirements (資料解析度要求)

| Calculation Type | Recommended Resolution | Notes |
|------------------|------------------------|-------|
| Energy Cost (電能費) | Any resolution | Only total kWh per period matters |
| Demand Penalty (違約金) | **15 minutes** | Taipower uses 15-min average for contract capacity |
| Basic Fee (基本費) | N/A | Based on contract capacity, not usage |

**Critical for Industrial Users:**
Taipower calculates demand penalties based on **15-minute average demand** (臺電詳細電價表：最高需量以15分鐘平均計算).
Using hourly or coarser data for `demand_kw` may significantly underestimate peak demand and penalty charges. See Section 4 for detailed guidance.

## API Quickstart (API 使用範例)

This guide covers the primary functions for querying plans, checking rates, and calculating costs.

### 1. Plan Information (查詢方案資訊)

**List Available Plans:**

```python
import tou_calculator as tou

print(tou.available_plans())
# 20 plans available with bilingual names:
# 表燈非時間電價 Residential Non-TOU
# 簡易型二段式 Simple 2-Tier
# ... (and more)
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
Holiday data is loaded with fallback priority: API → lunar calendar calculation → static preset.

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
print(f"Season: {context['season'].iloc[0]}")  # SeasonType.SUMMER
print(f"Period: {context['period'].iloc[0]}")  # PeriodType.PEAK
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

#### ⚠️ Important: Data Resolution Requirements (資料解析度要求)

**Taiwan Power Company's Official Standard (臺電官方規定)**

According to Taipower's official tariff regulations (詳細電價表 第八章), contract capacity and demand penalties are calculated based on **15-minute average demand**:
 臺電官方規定：契約容量與違約金以 **15 分鐘平均** 計算。

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
bill = calculate_bill(usage, "high_voltage_2_tier", inputs=inputs)
print(f"This Month's Bill: {bill['total'].iloc[0]:.0f} TWD")
```

**Detailed Bill Breakdown:**
If you need to know exactly how the bill was composed (e.g., how much was the Power Factor deduction):
若您需要了解帳單的詳細組成（例如力率折扣金額）：

```python
from tou_calculator import calculate_bill_breakdown

result = calculate_bill_breakdown(usage, "high_voltage_2_tier", inputs=inputs)

print("Summary:")
print(result["summary"])

print("\nLine Item Details:")
print(result["details"].head())  # Detailed period-by-period breakdown
print(result["adjustment_details"])  # Specific adjustments (e.g., PF discount amounts)
```

## Public API Index (公開 API 總覽)

Quick index of all public entry points exported by `tou_calculator`.

### Core helpers (核心入口)
- `available_plans()` list available plan IDs
- `plan(name, ...)` get a `TariffPlan` by plan ID
- `plan_details(name, ...)` return structured plan schema
- `period_at(target, plan_name, ...)` return period enum at timepoint
- `period_context(target, plan_name, ...)` return season/day/period context
- `pricing_context(target, plan_name, usage=None, include_details=False, ...)` pricing at timepoint
- `costs(usage, plan_name, ...)` energy cost series (wrapper)
- `monthly_breakdown(usage, plan_name, include_shares=False, ...)` monthly usage/cost summary

### Billing helpers (帳單計算)
- `BillingInputs` billing configuration model
- `calculate_bill(usage, plan_name, inputs)` full bill DataFrame
- `calculate_bill_breakdown(usage, plan_name, inputs)` bill + line items
- `calculate_bill_simple(usage, plan_name)` minimal bill calculation
- `calculate_bill_from_list(usage, plan_id, start, freq, ...)` calculate from list values (no pandas needed)
- `calculate_bill_from_dict(usage, plan_id, ...)` calculate from timestamp dict (no pandas needed)

### Calendar & tariff access (日曆與費率)
- `taiwan_calendar(...)` cached Taiwan holiday calendar
- `custom_calendar(...)` create a custom calendar instance
- `is_holiday(target, ...)` holiday check
- `TariffFactory` data-driven plan loader

### Custom plan builders (自定義方案)
- `build_tariff_profile(...)` create profile
- `build_tariff_rate(...)` create rate definition
- `build_day_schedule(...)` create day schedule
- `build_tariff_plan(...)` create `TariffPlan`
- `WeekdayDayTypeStrategy` simple weekday/weekend strategy

### Types & enums (型別與列舉)
- `TariffPlan`, `TariffProfile`
- `PeriodType`, `SeasonType`

### Errors (錯誤型別)
- `PowerKitError`, `CalendarError`, `TariffError`, `InvalidUsageInput`

## API Examples (公開 API 範例)

Short examples for each public entry point. Imports are shown once to keep this section compact.

```python
import tou_calculator as tou
import pandas as pd
from datetime import datetime
from tou_calculator import (
    BillingInputs,
    TariffFactory,
    TariffPlan,
    TariffProfile,
    PeriodType,
    SeasonType,
    PowerKitError,
)
```

### Core helpers (核心入口)

```python
# available_plans
print(tou.available_plans())

# plan + plan_details
plan = tou.plan("residential_simple_2_tier")
details = tou.plan_details("residential_simple_2_tier")

# period_at + period_context
dt = datetime(2025, 7, 15, 14, 0)
print(tou.period_at(dt, "residential_simple_2_tier"))
print(tou.period_context(dt, "residential_simple_2_tier"))

# pricing_context wrapper (uses plan_name)
print(tou.pricing_context(dt, "residential_simple_2_tier"))
print(tou.pricing_context(dt, "residential_simple_2_tier", usage=2.5, include_details=True))

# costs + monthly_breakdown
usage = pd.Series([1.5, 2.0, 1.8], index=pd.date_range("2025-07-15 14:00", periods=3, freq="h"))
print(tou.costs(usage, "residential_simple_2_tier"))
print(tou.monthly_breakdown(usage, "residential_simple_2_tier"))
```

### Billing helpers (帳單計算)

```python
inputs = BillingInputs(contract_capacities={"regular": 200}, power_factor=95.0)

print(tou.calculate_bill(usage, "high_voltage_2_tier", inputs=inputs))
print(tou.calculate_bill_breakdown(usage, "high_voltage_2_tier", inputs=inputs))
print(tou.calculate_bill_simple(usage, "high_voltage_2_tier"))

# Convenience functions - no pandas required
print(tou.calculate_bill_from_list([1.0, 1.5, 2.0], "residential_simple_2_tier", start="2025-07-15", freq="1h"))
print(tou.calculate_bill_from_dict({"2025-07-15 09:00": 1.0, "2025-07-15 10:00": 1.5}, "residential_simple_2_tier"))
```

### Calendar & tariff access (日曆與費率)

```python
# taiwan_calendar + is_holiday
calendar = tou.taiwan_calendar()
print(calendar.is_holiday(datetime(2025, 1, 1)))
print(tou.is_holiday(datetime(2025, 1, 1)))

# custom_calendar
custom = tou.custom_calendar(holidays={"2025-01-02"})
print(custom.is_holiday(datetime(2025, 1, 2)))

# TariffFactory
factory = TariffFactory()
plan = factory.create("residential_simple_2_tier", calendar=calendar)
```

### Custom plan builders (自定義方案)

```python
from tou_calculator import (
    build_tariff_profile,
    build_tariff_rate,
    build_day_schedule,
    build_tariff_plan,
    WeekdayDayTypeStrategy,
)

profile = build_tariff_profile(
    name="demo_plan",
    seasons=["summer", "non_summer"],
    day_types=["weekday", "weekend"],
    period_types=["peak", "off_peak"],
)
rate = build_tariff_rate(
    season="summer",
    day_type="weekday",
    period_type="peak",
    rate=5.0,
)
schedule = build_day_schedule(
    period_map=[("08:00", "22:00", "peak")],
    default_period="off_peak",
)
plan = build_tariff_plan(
    profile=profile,
    rates=[rate],
    schedules={"weekday": schedule, "weekend": schedule},
    day_type_strategy=WeekdayDayTypeStrategy(),
)
```

### Types & enums (型別與列舉)

```python
def accepts_types(plan: TariffPlan, profile: TariffProfile) -> tuple[TariffPlan, TariffProfile]:
    return plan, profile

print(PeriodType.PEAK, SeasonType.SUMMER)
```

### Errors (錯誤型別)

```python
try:
    tou.plan("unknown_plan")
except PowerKitError as exc:
    print("powerkit error:", exc)
except Exception as exc:
    print("other error:", exc)
```

## Available Plans (可用方案)

All 20 Taipower plans are now supported. Plans are organized by category:

| Category | Plans |
|----------|-------|
| **Residential** | `residential_non_tou`, `residential_simple_2_tier`, `residential_simple_3_tier` |
| **Lighting** | `lighting_non_business_tiered`, `lighting_business_tiered`, `lighting_standard_2_tier`, `lighting_standard_3_tier` |
| **Low Voltage** | `low_voltage_power`, `low_voltage_2_tier`, `low_voltage_three_stage`, `low_voltage_ev` |
| **High Voltage** | `high_voltage_power`, `high_voltage_2_tier`, `high_voltage_three_stage`, `high_voltage_batch`, `high_voltage_ev` |
| **Extra High Voltage** | `extra_high_voltage_power`, `extra_high_voltage_2_tier`, `extra_high_voltage_three_stage`, `extra_high_voltage_batch` |

## Performance (效能效能)

The library is optimized for processing large time-series datasets efficiently through vectorized calendar queries and intelligent caching.

### Benchmark Results (基準測試結果)

| Data Size | Processing Time | Throughput | Use Case |
|-----------|-----------------|------------|----------|
| 1,000 records | ~0.01s | ~75K records/s | Small household (1 month hourly) |
| 10,000 records | ~0.01s | ~900K records/s | Medium household (1 year hourly) |
| 100,000 records | ~0.4s | ~240K records/s | Large analysis (10+ years hourly) |
| 1,000,000 records | ~4s | ~250K records/s | Industrial scale analysis |

*First run may take longer due to API calls and cache generation. Subsequent runs use cached data and are significantly faster.*

### Optimization Features (最佳化特性)

1. **Vectorized Calendar Queries (向量化日曆查詢)**
   - Batch processing of unique dates instead of individual lookups
   - Reduces calendar API calls from O(n) to O(unique dates)

2. **Smart API Handling (智慧 API 處理)**
   - Skips API fetch for future years (beyond current year + 1)
   - Prevents timeout delays for non-existent calendar data
   - Falls back to lunar calendar calculation when needed

3. **Memory Caching (記憶體快取)**
   - Holiday data cached per year in memory
   - Subsequent queries for same year are O(1) lookups

4. **Efficient Sunday Calculation (高效週日計算)**
   - Direct calculation without iteration through all days
   - ~50x faster than naive date-by-date iteration

### Tips for Best Performance (效能最佳化建議)

```python
# For very large datasets, preload years in advance
calendar = tou.taiwan_calendar()
calendar.preload_years({2024, 2025, 2026})  # Preload multiple years

# Then use the cached calendar
plan = tou.plan("residential_simple_2_tier", calendar_instance=calendar)
costs = plan.calculate_costs(usage_data)  # Will use cached holidays
```

## Custom Plans (自定義費率)

You can also define custom calendars and rate schedules if the built-in Taipower plans don't fit your needs. (See `src/tou_calculator/custom.py` or the tests for advanced examples).

---

## Quality & Testing (品質與測試)

This library is production-ready with comprehensive test coverage:

### Test Coverage (測試覆蓋率)
- **364 tests** across 12 test modules
- **100% pass rate** on Python 3.9, 3.10, 3.11, 3.12, 3.13
- Accuracy validated against Taipower official rates
- Stress tested with 5M+ records

### Test Categories
| Category | Tests | Description |
|----------|-------|-------------|
| Unit Tests | 127 | Core functionality testing |
| Integration | 54 | Multi-component workflows |
| Accuracy | 38 | Taipower rate verification |
| Stress | 41 | Performance & load testing |
| Production | 104 | Security, encoding, edge cases |

### Code Quality
- **Linting:** ruff (PEP 8 compliant)
- **Type checking:** mypy (type hints validated)
- **Pre-commit:** Automated quality checks
- **CI/CD:** GitHub Actions on every push

### License
MIT License - see [LICENSE](LICENSE) for details.

---

## Links (相關連結)

- **Repository:** https://github.com/JUN-WEI-DING/tou_calculator
- **Issues:** https://github.com/JUN-WEI-DING/tou_calculator/issues
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)
- **License:** [MIT](LICENSE)
