[![PyPI Version](https://img.shields.io/pypi/v/tou-calculator)](https://pypi.org/project/tou-calculator/)
[![Python](https://img.shields.io/pypi/pyversions/tou-calculator)](https://pypi.org/project/tou-calculator/)
[![License](https://img.shields.io/github/license/JUN-WEI-DING/tou_calculator)](https://github.com/JUN-WEI-DING/tou_calculator/blob/main/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/JUN-WEI-DING/tou_calculator/ci.yml?branch=main)](https://github.com/JUN-WEI-DING/tou_calculator/actions/workflows/ci.yml)

# Taiwan Electricity Tariff Calculator

**Confused by Taipower's complex rates? / 台電費率複雜，每次都搞不清楚嗎？**
A comprehensive tool for calculating electricity costs based on Taiwan Power Company's (Taipower) pricing schemes.

This library supports **both** major tariff types used by Taipower:
- **Tiered Rate Plans (累進費率)**: Rates increase progressively with usage (traditional residential/commercial)
- **Time-of-Use Plans (時間電價)**: Rates vary by time period, season, and day type

It encapsulates complex rules—including seasonal variations, holiday logic, and multi-stage rate schedules—into a simple, easy-to-use API.

臺灣電價計算工具，支援 **累進費率** 與 **時間電價** 兩種主要計費方式。

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

## Quick Start Guide (快速入門)

Choose the section that matches your tariff type:
根據您的電價方案選擇對應章節：

- **[Tiered Rate Plans (累進費率)](#tiered-rate-quick-start)** - For `residential_non_tou`, `lighting_*_tiered`, etc.
- **[Time-of-Use Plans (時間電價)](#time-of-use-quick-start)** - For `*_simple_*_tier`, `*_2_tier`, `*_three_stage`, etc.

---

## Tiered Rate Quick Start (累進費率快速入門)

This section is for **tiered rate plans** where the rate per kWh increases progressively with your total usage (traditional residential/commercial billing).

這個章節適用於 **累進費率方案**，費率會隨著總用電量增加而上調（傳統住家/商業計費方式）。

### Which Plans Use Tiered Rates? (哪些方案使用累進費率？)

| Plan ID | 中文名稱 | Description |
|---------|---------|-------------|
| `residential_non_tou` | 表燈非時間電價 | Standard residential tiered rates |
| `lighting_non_business_tiered` | 表燈非營業（累進） | Non-business lighting with tiers |
| `lighting_business_tiered` | 表燈營業（累進） | Business lighting with tiers |

### Understanding Tiered Rates (瞭解累進費率)

In tiered rate plans, electricity cost is calculated based on **total monthly usage**, with higher rates for higher consumption brackets:

累進費率方案根據 **每月總用電量** 計算，用電越多，單價越高：

```
Example: Residential Non-TOU (表燈非時間電價)
Non-Summer (非夏月):
  0 - 120 kWh:    1.78 TWD/kWh
  121 - 330 kWh:  2.26 TWD/kWh
  331 - 500 kWh:  3.13 TWD/kWh
  501 - 700 kWh:  4.24 TWD/kWh
  701 - 1000 kWh: 5.27 TWD/kWh
  1001+ kWh:      7.03 TWD/kWh

Summer (夏月，6-9月):
  0 - 120 kWh:    1.78 TWD/kWh
  121 - 330 kWh:  2.55 TWD/kWh
  331 - 500 kWh:  3.80 TWD/kWh
  501 - 700 kWh:  5.14 TWD/kWh
  701 - 1000 kWh: 6.44 TWD/kWh
  1001+ kWh:      8.86 TWD/kWh
```

### Basic Example (基本範例)

```python
import pandas as pd
import tou_calculator as tou

# Your monthly usage data (one value per month)
# 你的每月用電資料（每個月一個值）
monthly_usage = pd.Series(
    [280, 320, 250, 310, 290, 280, 350, 380, 360, 300, 270, 260],
    index=pd.date_range("2025-01-01", periods=12, freq="MS")
)

# Calculate with tiered rate plan
# 使用累進費率方案計算
plan = tou.plan("residential_non_tou")
costs = plan.calculate_costs(monthly_usage)

print(f"Annual Total: {costs.sum():.2f} TWD")
# Output: Annual Total: 7940.90 TWD

# View monthly breakdown
# 檢視每月明細
for month, cost in costs.items():
    print(f"{month.strftime('%Y-%m')}: {cost:.2f} TWD")
# 2025-01: 575.20 TWD
# 2025-02: 665.60 TWD
# ...
```

### Detailed Breakdown (詳細明細)

```python
# See how each month was calculated
# 檢視每個月的計算明細
report = plan.monthly_breakdown(monthly_usage)
print(report)
#         month    season period  usage_kwh   cost
# 0  2025-01-01  non_summer  tiered      280.0  575.2
# 1  2025-02-01  non_summer  tiered      320.0  665.6
# ...
```

### Using List/Dict (使用 List 或 Dict)

**Note:** For tiered rate plans, it's recommended to use `plan.calculate_costs()` directly. The convenience functions below are primarily designed for time-of-use plans.
累進費率方案建議直接使用 `plan.calculate_costs()` 方法。

```python
# For tiered rates, use plan.calculate_costs() with pandas Series
# 累進費率建議使用 pandas Series + plan.calculate_costs()
import pandas as pd
import tou_calculator as tou

usage = [280, 320, 250, 310]  # Monthly kWh readings
dates = pd.date_range("2025-01-01", periods=len(usage), freq="MS")
series = pd.Series(usage, index=dates)

plan = tou.plan("residential_non_tou")
costs = plan.calculate_costs(series)
print(f"4-Month Total: {costs.sum():.2f} TWD")
```

If you prefer using list/dict for tiered rates, specify `billing_cycle_months=1`:
如果一定要用 list/dict 計算累進費率，需要指定 `billing_cycle_months=1`：

```python
from tou_calculator import calculate_bill, BillingInputs

dates = pd.date_range("2025-01-01", periods=4, freq="MS")
series = pd.Series([280, 320, 250, 310], index=dates)

inputs = BillingInputs(billing_cycle_months=1)
result = calculate_bill(series, "residential_non_tou", inputs=inputs)
print(f"4-Month Total: {result['total'].sum():.2f} TWD")
```

### Single Month Calculation (單月計算)

```python
# Calculate cost for a single month's usage
# 計算單月用電費用
plan = tou.plan("residential_non_tou")
monthly_kwh = 350  # Total kWh for the month

# Create a single-entry series
usage = pd.Series([monthly_kwh], index=pd.date_range("2025-07-01", periods=1, freq="MS"))
cost = plan.calculate_costs(usage).iloc[0]

print(f"Usage: {monthly_kwh} kWh")
print(f"Cost: {cost:.2f} TWD")
print(f"Average: {cost/monthly_kwh:.2f} TWD/kWh")
```

### Two-Month Billing Cycle (隔月抄表)

Taiwan Power Company (Taipower) implements **bimonthly meter reading and billing** for most residential and small business customers. This library fully supports this billing cycle with automatic tier limit doubling and rate change apportionment.

臺灣對一般住宅及小商店實施 **隔月抄表收費制度**，本函式庫完整支援此抄表週期，包含級距上限加倍及電價異動分攤計算。

#### Why Bimonthly Billing? (為何實施隔月抄表？)

Since July 1985, Taipower has implemented bimonthly meter reading for residential and small business customers to:
- **Reduce customer disturbance** (fewer meter reading visits)
- **Save paper** (fewer paper bills mailed, supporting carbon reduction)

自民國 74 年 7 月起，臺電對一般住宅及小商店使用者實施隔月抄表收費制度，目的在於：
- **減少打擾使用者**（降低抄表次數）
- **節省紙張**（減少紙本帳單郵寄，配合節能減碳政策）

About half of customers are metered in **odd months** (1, 3, 5, 7, 9, 11), and the other half in **even months** (2, 4, 6, 8, 10, 12).

約半數使用者係在 **單數月份** (1, 3, 5, 7, 9, 11 月) 抄表，其餘使用者則在 **雙數月份** (2, 4, 6, 8, 10, 12 月) 抄表。

#### Understanding Bimonthly Billing

| Meter Reading Cycle | Billing Periods (計費週期) | Meter Read Month (抄表月份) |
|---------------------|--------------------------|---------------------------|
| **Odd Month (奇數月抄表)** | 12月-1月, 2月-3月, 4月-5月, 6月-7月, 8月-9月, 10月-11月 | 1, 3, 5, 7, 9, 11月 |
| **Even Month (偶數月抄表)** | 1月-2月, 3月-4月, 5月-6月, 7月-8月, 9月-10月, 11月-12月 | 2, 4, 6, 8, 10, 12月 |

##### Tier Limit Doubling (級距度數加倍)

> **Official Taipower Policy**: After adopting bimonthly meter reading, customer billing tier limits are **doubled** according to the tariff table.
> **臺電官方說明**：採隔月抄表後，使用者計費之分段度數亦均依電價表之各級距度數加倍計算。

For example, for residential customers:
- **Monthly billing**: First 120 kWh at 1.78 TWD/kWh
- **Bimonthly billing**: First 240 kWh at 1.78 TWD/kWh (tier limit doubled)

例如住宅使用者：
- **每月抄表**：120 度以內每度 1.78 元
- **隔月抄表**：240 度以內每度 1.78 元（級距加倍）

> This does **not increase** the customer's electricity burden—the tier limits simply cover a 2-month period instead of 1 month.
> 並不會增加使用者電費負擔——級距上限只是涵蓋兩個月而非一個月。

##### Rate Change Apportionment (電價異動分攤)

> **Official Taipower Policy**: When usage crosses different rate periods (e.g., seasonal price changes or rate adjustments), usage is apportioned by the ratio of days before/after the change date.
> **臺電官方說明**：用電橫跨不同電價期間時，將抄表期間的用電度數，按照電價異動前後日數佔全期用電日數之比例分攤。

This **day-ratio apportionment method** is commonly adopted by power companies worldwide during rate adjustments and has been implemented in Taiwan for many years.

此種 **按日數比例分攤度數方式** 向為各國電力公司在調整電價時所普遍採行，我國亦已實施多年。

#### Using Bimonthly Billing

```python
import pandas as pd
import tou_calculator as tou
from tou_calculator import BillingCycleType

# Usage for June-July (2 months)
dates = pd.date_range("2025-06-01", "2025-07-31", freq="D")
usage = pd.Series([5] * len(dates), index=dates)  # ~305 kWh total

# Odd-month billing (meter read in July for June-July period)
plan_odd = tou.plan("residential_non_tou", billing_cycle_type=BillingCycleType.ODD_MONTH)
costs_odd = plan_odd.calculate_costs(usage)

# Even-month billing (for May-June data, use April-May period or use appropriate dates)
# Note: Even-month billing periods are (1,2)->2, (3,4)->4, (5,6)->6, etc.
# For June-July data, you'd typically use odd-month billing instead
plan_even = tou.plan("residential_non_tou", billing_cycle_type=BillingCycleType.EVEN_MONTH)

# Monthly billing (default)
plan_monthly = tou.plan("residential_non_tou")  # or BillingCycleType.MONTHLY

print(f"Odd-month billing (June-July): {costs_odd.sum():.2f} TWD")
print(f"Tier limit for 2-month period: 240 kWh (doubled from 120 kWh)")
```

#### Billing Cycle Comparison

```python
# Example: 240 kWh over 2 months
usage_240 = pd.Series([4] * 60, index=pd.date_range("2025-06-01", periods=60, freq="D"))

# Monthly: 120 kWh/month, each in tier 1 (0-120 kWh)
plan_monthly = tou.plan("residential_non_tou")
cost_monthly = plan_monthly.calculate_costs(usage_240)

# Bimonthly: 240 kWh total, still in tier 1 (0-240 kWh for 2-month period)
plan_odd = tou.plan("residential_non_tou", billing_cycle_type=BillingCycleType.ODD_MONTH)
cost_bimonthly = plan_odd.calculate_costs(usage_240)

# Same total cost! (tier limit doubled for bimonthly billing)
print(f"Monthly billing total: {cost_monthly.sum():.2f} TWD")
print(f"Bimonthly billing total: {cost_bimonthly.sum():.2f} TWD")
```

---

## Time-of-Use Quick Start (時間電價快速入門)

This section is for **time-of-use (TOU) plans** where rates vary by time period (peak/off-peak), season, and day type.
這個章節適用於 **時間電價方案**，費率會隨時段、季節和日期型別而變動。

### Which Plans Use TOU Rates? (哪些方案使用時間電價？)

| Category | Plan IDs | 中文名稱 |
|----------|----------|---------|
| **Residential** | `residential_simple_2_tier`, `residential_simple_3_tier` | 簡易型二段式、三段式 |
| **Lighting** | `lighting_standard_2_tier`, `lighting_standard_3_tier` | 表燈標準二段式、三段式 |
| **Low Voltage** | `low_voltage_2_tier`, `low_voltage_three_stage`, `low_voltage_ev`, `low_voltage_power` | 低壓電力二段式、三段式、EV、綜合 |
| **High Voltage** | `high_voltage_2_tier`, `high_voltage_three_stage`, `high_voltage_ev`, `high_voltage_power`, `high_voltage_batch` | 高壓電力二段式、三段式、EV、綜合、包表 |
| **Extra High Voltage** | `extra_high_voltage_2_tier`, `extra_high_voltage_three_stage`, `extra_high_voltage_power`, `extra_high_voltage_batch` | 特高壓電力二段式、三段式、綜合、包表 |

### Understanding TOU Rates (瞭解時間電價)

In TOU plans, rates vary based on **when** you use electricity:
時間電價方案根據 **何時** 用電來計費：

| Factor | Options | Impact on Rate |
|--------|---------|----------------|
| **季節 Season** | 夏月 Summer (6-9月) / 非夏月 Non-Summer | Summer rates ≈ 20-40% higher |
| **日期 Day Type** | 週日+國定假日 / 週六 Saturday / 平日 Weekday | Holidays get off-peak rates |
| **時段 Period** | 尖峰 Peak / 半尖峰 Semi-Peak / 離峰 Off-Peak | Peak most expensive, off-peak cheapest |

### Step 1: Prepare Your Time-Series Data (準備時間序列資料)

TOU plans need **hourly or finer** time-series data to calculate different rates for different periods.
時間電價需要 **小時或更細** 的時間序列資料來計算不同時段的費率。

#### Example A: Create Data Manually (範例 A：用 Python 手動建立資料)

```python
import pandas as pd

# Method 1: Using list
# 方法 1：用 list 建立
timestamps = [
    "2025-07-15 09:00",  # July 15, 2025, 9:00 AM (summer weekday - peak)
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
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.set_index("timestamp")
usage_series = df["usage"]
```

#### Example C: No-Pandas Functions (無需 Pandas 的便利函式)

```python
import tou_calculator as tou

# Using list (for regularly-spaced data)
# 使用 list（適用於固定間隔資料）
result = tou.calculate_bill_from_list(
    usage=[1.5, 2.3, 1.8, 2.0, 1.6],
    plan_id="簡易型二段式",
    start="2025-07-15 09:00",
    freq="1h",  # 1-hour interval
)
print(f"Total: {result['total'].iloc[0]:.2f} TWD")

# Using dict (for irregularly-spaced data)
# 使用 dict（適用於不規則間隔資料）
result = tou.calculate_bill_from_dict(
    usage={
        "2025-07-15 09:00": 1.5,
        "2025-07-15 10:00": 2.3,
        "2025-07-15 14:30": 2.0,  # Different interval OK
    },
    plan_id="residential_simple_2_tier",
)
print(f"Total: {result['total'].iloc[0]:.2f} TWD")
```

### Step 2: Check Rate Period (判斷費率時段)

Before calculating, you can check what rate period applies at a specific time.
計算前可以先查詢特定時間屬於哪個費率時段。

```python
from datetime import datetime
import tou_calculator as tou

dt = datetime(2025, 7, 15, 14, 0)  # July 15, 2025, 2:00 PM (summer weekday afternoon)

# Check period type
# 查詢時段型別
period = tou.period_at(dt, "residential_simple_2_tier")
print(f"Period: {period}")  # Output: PeriodType.PEAK (尖峰)

# Check if it's a holiday
# 檢查是否為國定假日
is_holiday = tou.is_holiday(dt)
print(f"Is Holiday: {is_holiday}")  # Output: False

# Get pricing context (rate + more details)
# 取得費率資訊
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

### Step 3: Calculate Costs (計算電費)

#### Using pandas Series (推薦用於大型資料集)

```python
# Get plan object
# 取得方案物件
plan = tou.plan("residential_simple_2_tier")

# Calculate costs (returns monthly aggregated costs)
# 計算電費（返回按月匯總的電費）
costs = plan.calculate_costs(usage_series)

# View results
# 看結果
print(f"Total Cost: {costs.iloc[0]:.2f} TWD")
```

#### Using List/Dict (無需 pandas)

```python
# For regularly-spaced hourly data
# 對於每小時固定間隔的資料
result = tou.calculate_bill_from_list(
    usage=[1.2, 1.5, 1.8, 2.1, 1.6, 1.4, 1.3, 1.7],
    plan_id="residential_simple_2_tier",
    start="2025-07-15 09:00",
    freq="1h",
)
print(f"Total: {result['total'].iloc[0]:.2f} TWD")
```

### Step 4: View Detailed Report (檢視詳細報表)

```python
# View monthly statistics by period
# 檢視每月各時段統計
report = plan.monthly_breakdown(usage_series)
print(report)
#        month  season period  usage_kwh    cost
# 0 2025-07-01  summer   peak        5.6  28.896
# 1 2025-07-01  summer off_peak       2.4   6.720
```

### Step 5: Advanced Calculation (進階計算)

For industrial users with contract capacity, basic fees, and penalties:
適合有契約容量的工業使用者（含基本費和違約金）：

```python
from tou_calculator import calculate_bill, BillingInputs

# Configure billing parameters
# 設定計費引數
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

**Important:** For penalty calculation, use **15-minute interval** demand data. See [Data Resolution Requirements](#data-resolution-requirements) below.
**重要：** 違約金計算請使用 **15 分鐘間隔** 的需量資料。詳見下方的[資料解析度要求](#data-resolution-requirements)。

### Complete Example (完整範例)

```python
import pandas as pd
import tou_calculator as tou

# 1. Load hourly usage data
# 1. 讀取每小時用電資料
df = pd.read_csv("my_usage.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.set_index("timestamp")

# 2. Get TOU plan
# 2. 取得時間電價方案
plan = tou.plan("residential_simple_2_tier")

# 3. Calculate costs
# 3. 計算電費
costs = plan.calculate_costs(df["usage"])

# 4. View breakdown by period
# 4. 檢視各時段明細
report = plan.monthly_breakdown(df["usage"])
print(report)

# 5. Print summary
# 5. 印出摘要
print(f"Total Cost: {costs.sum():.2f} TWD")
print(f"Total Usage: {df['usage'].sum():.2f} kWh")
print(f"Average: {costs.sum() / df['usage'].sum():.2f} TWD/kWh")
```

---

## Calculation Logic & Background (計算邏輯與背景)

This section explains how Taiwan Power Company (Taipower) calculates electricity bills. Understanding this helps you verify the results and optimize your electricity usage.
這個章節說明臺電如何計算電費，瞭解這些可以幫助你驗證結果並最佳化用電。

### Quick Formula (電費計算公式)

```
總電費 = 電能費 + 基本費 + 違約金 ± 功率因數調整 + 其他調整

Total Bill = Energy Cost + Basic Fee + Penalty ± PF Adjustment + Others
```

---

## Tiered Rate Calculation (累進費率計算方式)

For tiered rate plans (non-TOU), energy cost is calculated based on **total monthly usage** with progressively higher rates.
累進費率方案根據 **每月總用電量** 計算，用電越多單價越高。

### How Tiered Rates Work (累進費率運作方式)

```
電能費 = Σ(各累進級距用電度數 × 該級距單價)

Energy Cost = Σ(Tier_kWh × Tier_Rate) for each tier
```

**Example: Residential Non-TOU (表燈非時間電價) - Summer**

| Usage Range (kWh) | Rate (TWD/kWh) | Example Calculation |
|-------------------|----------------|---------------------|
| 0 - 120 | 1.78 | First 120 kWh × 1.78 |
| 121 - 330 | 2.55 | Next 210 kWh × 2.55 |
| 331 - 500 | 3.80 | Next 170 kWh × 3.80 |
| 501 - 700 | 5.14 | Next 200 kWh × 5.14 |
| 701 - 1000 | 6.44 | Next 300 kWh × 6.44 |
| 1001+ | 8.86 | Remaining kWh × 8.86 |

**Sample Calculation for 350 kWh in Summer:**

| Tier | Usage | Rate | Cost |
|------|-------|------|------|
| 1st tier (0-120) | 120 kWh | 1.78 | 213.60 |
| 2nd tier (121-330) | 210 kWh | 2.55 | 535.50 |
| 3rd tier (331-500) | 20 kWh | 3.80 | 76.00 |
| **Total** | **350 kWh** | - | **825.10 TWD** |

### Factors Affecting Tiered Rates (影響累進費率的因素)

| Factor | Options | Impact |
|--------|---------|--------|
| **季節 Season** | 夏月 Summer (6-9月) / 非夏月 Non-Summer | Summer rates are ~6-10% higher |
| **累進級距 Tiers** | 5 or 6 tiers depending on plan | Higher usage = higher rate applies |

---

## Time-of-Use Calculation (時間電價計算方式)

For TOU plans, energy cost is calculated based on **when** you use electricity.
時間電價方案根據 **何時** 用電來計算電費。

### How TOU Rates Work (時間電價運作方式)

```
電能費 = Σ(各時段用電度數 × 該時段費率)

Energy Cost = Σ(Period_Usage_kWh × Period_Rate) for each time period
```

**Rate varies by:**

| Factor | Options | Impact on Rate |
|--------|---------|----------------|
| **季節 Season** | 夏月 Summer (6-9月) / 非夏月 Non-Summer | Summer rates ≈ 20-40% higher |
| **日期 Day Type** | 週日+國定假日 Sunday+Holidays / 週六 Saturday / 平日 Weekday | Holidays get off-peak rates |
| **時段 Period** | 尖峰 Peak / 半尖峰 Semi-Peak / 離峰 Off-Peak | Peak most expensive, off-peak cheapest |

**Sample TOU Schedule (簡易型二段式):**

| Day Type | Period | Hours | Rate (Summer) |
|----------|--------|-------|---------------|
| Weekday | Peak | 07:00-23:00 | 5.16 TWD/kWh |
| Weekday | Off-peak | 23:00-07:00 | 2.06 TWD/kWh |
| Saturday | Semi-peak | All day | 3.19 TWD/kWh |
| Sunday/Holiday | Off-peak | All day | 2.06 TWD/kWh |

---

## Common Components (共同計算元件)

These components apply to both tiered rate and TOU plans.
這些元件同樣適用於累進費率和時間電價方案。

### 1. Basic Fee (基本費) - Contract Capacity × Unit Price

**A fixed monthly fee based on your contracted power capacity.**
基於契約容量的固定月費。

```
基本費 = 契約容量 × 單價
Basic Fee = Contract Capacity(kW) × Unit Rate
```

| Fee Type | Description | Who Pays This |
|----------|-------------|---------------|
| **經常契約** | Regular contract capacity (year-round) | All contract users |
| **非夏月契約** | Additional non-summer capacity | High-voltage users |
| **半尖峰契約** | Semi-peak capacity | 3-stage TOU users |
| **週六半尖峰契約** | Saturday semi-peak capacity | 2/3-stage TOU users |
| **離峰契約** | Off-peak capacity | 2/3-stage TOU users |

**Note:** Basic fee only applies to plans with contract capacity (industrial/commercial TOU plans).
**說明：** 基本費僅適用於有契約容量的方案（工業/商業時間電價）。

---

### 2. Demand Penalty (違約金) - Exceeding Contract Capacity

**If your peak demand exceeds your contract capacity, you pay a penalty.**
如果最高需量超過契約容量，需支付違約金。

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

### 3. Power Factor Adjustment (功率因數調整)

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

### 4. Complete Bill Example (完整帳單範例)

**Scenario:** High-voltage factory in July (summer)

| Item | Calculation | Amount (TWD) |
|------|-------------|--------------|
| Energy Cost (Peak) | 10,000 kWh × $5.16 | 51,600 |
| Energy Cost (Off-peak) | 20,000 kWh × $2.06 | 41,200 |
| **Energy Cost (Subtotal)** | 92,800 (sum) | **92,800** |
| Basic Fee | 200 kW × $236.20 | 47,240 |
| Penalty | (230-200) kW × $236.20 × 2 | 14,172 |
| PF Discount | -47,240 × 1.5% | -709 |
| **Total** | 153,503 (sum) | **153,503** |

---

### 5. Data Resolution Requirements (資料解析度要求)

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

plans = tou.available_plans()
for plan_id, chinese_name in plans.items():
    print(f"{plan_id}: {chinese_name}")

# residential_non_tou: 表燈非時間電價
# residential_simple_2_tier: 簡易型二段式
# ... (20 plans total)
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

**Note:** `period_at()` returns `PeriodType` enum (e.g., `PeriodType.PEAK`), while `pricing_context()` returns string (e.g., `"peak"`).

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
- `available_plans()` returns dict of {plan_id: chinese_name}
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
# 便利函式 - 不需要 pandas

# calculate_bill_from_list: for regularly-spaced data
# calculate_bill_from_list: 適用於固定間隔資料
result_list = tou.calculate_bill_from_list(
    usage=[1.0, 1.5, 2.0, 1.8],
    plan_id="residential_simple_2_tier",
    start="2025-07-15 09:00",
    freq="1h",
)
print(result_list)
# Returns DataFrame with: [energy_cost, basic_cost, surcharge, adjustment, total]

# calculate_bill_from_dict: for irregularly-spaced data
# calculate_bill_from_dict: 適用於不規則間隔資料
result_dict = tou.calculate_bill_from_dict(
    usage={
        "2025-07-15 09:00": 1.0,
        "2025-07-15 10:30": 1.5,  # Different interval OK
        "2025-07-15 14:00": 2.0,
    },
    plan_id="residential_simple_2_tier",
)
print(result_dict)
```

### Calendar & tariff access (日曆與費率)

```python
# taiwan_calendar + is_holiday
calendar = tou.taiwan_calendar()
print(calendar.is_holiday(datetime(2025, 1, 1)))
print(tou.is_holiday(datetime(2025, 1, 1)))

# custom_calendar (requires date objects, not strings)
from datetime import date
custom = tou.custom_calendar(holidays=[date(2025, 1, 2)])
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

All 20 Taipower plans are supported. Plans are organized by billing type:
支援全部 20 種臺電方案，按計費方式分類：

### Tiered Rate Plans (累進費率方案)

Rates increase progressively based on monthly usage volume.
費率隨每月用電量逐級上調。

| Category | Plan ID | 中文名稱 |
|----------|---------|---------|
| **Residential** | `residential_non_tou` | 表燈非時間電價 |
| **Lighting** | `lighting_non_business_tiered` | 表燈非營業（累進） |
| **Lighting** | `lighting_business_tiered` | 表燈營業（累進） |

### Time-of-Use Plans (時間電價方案)

Rates vary by time period, season, and day type.
費率隨時段、季節和日期型別變動。

| Category | Plan ID | 中文名稱 |
|----------|---------|---------|
| **Residential** | `residential_simple_2_tier` | 簡易型二段式 |
| **Residential** | `residential_simple_3_tier` | 簡易型三段式 |
| **Lighting** | `lighting_standard_2_tier` | 表燈標準二段式 |
| **Lighting** | `lighting_standard_3_tier` | 表燈標準三段式 |
| **Low Voltage** | `low_voltage_2_tier` | 低壓電力二段式 |
| **Low Voltage** | `low_voltage_three_stage` | 低壓電力三段式 |
| **Low Voltage** | `low_voltage_ev` | 低壓電動車充電 |
| **Low Voltage** | `low_voltage_power` | 低壓電力綜合 |
| **High Voltage** | `high_voltage_2_tier` | 高壓電力二段式 |
| **High Voltage** | `high_voltage_three_stage` | 高壓電力三段式 |
| **High Voltage** | `high_voltage_ev` | 高壓電動車充電 |
| **High Voltage** | `high_voltage_power` | 高壓電力綜合 |
| **High Voltage** | `high_voltage_batch` | 高壓電力包表 |
| **Extra High Voltage** | `extra_high_voltage_2_tier` | 特高壓電力二段式 |
| **Extra High Voltage** | `extra_high_voltage_three_stage` | 特高壓電力三段式 |
| **Extra High Voltage** | `extra_high_voltage_power` | 特高壓電力綜合 |
| **Extra High Voltage** | `extra_high_voltage_batch` | 特高壓電力包表 |

## Performance (效能)

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
