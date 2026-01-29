# tou_calculator API 中文說明

本檔案列出目前公開 API 的功能、常用設定與回傳內容。所有範例請參考
`examples/usage_examples.py`。

## 行事曆與假日
- `taiwan_calendar(cache_dir=None, api_timeout=10)`
  - 功能：建立臺灣假日行事曆，必要時從公開 API 抓資料並快取。
  - 設定：`cache_dir` 指定快取資料夾；`api_timeout` 設定請求秒數。
- `is_holiday(target, calendar=None, cache_dir=None, api_timeout=10)`
  - 功能：判斷 `date` 或 `datetime` 是否為假日。
  - 設定：可傳入自訂 `calendar`；或傳 `cache_dir`/`api_timeout` 建立新行事曆。

## 方案
- `available_plans()`
  - 功能：列出支援的方案名稱。
- `plan(name, calendar_instance=None, cache_dir=None, api_timeout=10)`
  - 功能：用方案名稱取得 `TariffPlan`。
- `residential_simple_2_tier_plan(...)`
- `high_voltage_2_tier_plan(...)`
- `residential_non_tou_plan(...)`
  - 功能：直接取得對應方案的 `TariffPlan`。

## 時段與上下文
- `get_period(target, profile)`
  - 功能：用 `TariffProfile` 查詢時段型別。
  - 回傳：`PeriodType` 或 `pd.Series`。
- `period_at(target, plan_name, ...)`
  - 功能：用方案名稱查詢時段型別。
- `period_context(target, plan_name, ...)`
  - 功能：回傳 `season/day_type/period`。
  - 回傳：單點為 `dict`，多點為 `DataFrame`。
- `pricing_context(target, plan_name, usage=None, include_details=False, ...)`
  - 功能：回傳 `season/period/rate/cost`，支援單點與時間序列。
  - 設定：`usage` 可為單值或 `pd.Series`（僅適用時間電價方案）。
  - 補充：分級電價方案不提供逐時 `rate/cost`，需用月結算。
  - 補充：未提供 `usage` 時只會回 `rate`，`cost` 會是 `None`。
  - `include_details=True` 會附上 `rate_details` 與 `profile_details`。
  - 注意：電費計算仍以每月結算為主，請用 `calculate_costs`。

## 成本計算
- `calculate_costs(usage, plan)`
  - 功能：依月結算費用（回每月總費用 `pd.Series`）。
  - 設定：`usage` 必須是 `pd.Series`，index 為 `DatetimeIndex`。
- `costs(usage, plan_name, ...)`
  - 功能：用方案名稱計算每月費用。
- `calculate_bill(usage, plan_id, inputs=None, ...)`
  - 功能：依 `plans.json` 規則計算每月帳單費用（含基本費/加成/調整）。
  - 設定：`inputs` 為 `BillingInputs`，可傳契約容量、功率因數、電表設定等。
- `calculate_bill_simple(usage, plan_id, ...)`
  - 功能：快速計算每月帳單費用（不需進階引數）。
- `calculate_bill_breakdown(usage, plan_id, inputs=None, ...)`
  - 功能：回傳每月總表與時段明細（含每期用電與能量費）。
- `monthly_breakdown(usage, plan_name, include_shares=False, ...)`
  - 功能：依月彙總用電與費用，並按 `season/period` 分組。
  - 補充：分級電價方案會回傳每月一列，`period="tiered"`。
  - 設定：`include_shares=True` 會附上 `usage_share` 與 `cost_share`。

## 方案描述
- `plan_details(plan_name, ...)`
  - 功能：回傳完整方案結構（時段表與費率表）。

## 自訂方案
- `custom_calendar(holidays=None, weekend_days=None)`
  - 功能：用固定假日清單與週末規則建立自訂行事曆。
- `holidays` 可傳 `date` 清單；`weekend_days` 為星期幾清單（0=Mon, 6=Sun）。
- `WeekdayDayTypeStrategy(calendar, weekday_map=None, holiday_label="holiday")`
  - 功能：用星期幾與假日規則定義 day_type。
- `weekday_map` 預設 weekday/saturday/sunday；`holiday_label` 會覆蓋假日。
- `build_tariff_profile(...)`
  - 功能：用簡化的 schedules 定義建立 `TariffProfile`。
- `schedules` 可用 dict 或 list 形式；slot 內時間格式為 `"HH:MM"`，`"24:00"` 會被視為隔天 00:00。
- `default_period` 可設定無對應 slot 時的預設時段。
- `build_tariff_rate(...)`
  - 功能：用 period_costs 與 tiered_rates 定義建立 `TariffRate`。
- `period_costs` 可用 list 或 dict；period 允許 `PeriodType` 或自訂字串。
- `tiered_rates` 支援分級電價（`start_kwh/end_kwh/summer_cost/non_summer_cost`）。
- `build_tariff_plan(profile, rates)`
  - 功能：組合 `TariffProfile` 與 `TariffRate` 成 `TariffPlan`。

### 自訂方案範例

```python
from datetime import datetime
import tou_calculator as tou

calendar = tou.custom_calendar()
day_types = tou.WeekdayDayTypeStrategy(calendar)
season = tou.TaiwanSeasonStrategy((6, 1), (9, 30))

profile = tou.build_tariff_profile(
    name="Custom-Plan",
    season_strategy=season,
    day_type_strategy=day_types,
    schedules=[
        {
            "season": "summer",
            "day_type": "weekday",
            "slots": [
                {"start": "00:00", "end": "12:00", "period": "off_peak"},
                {"start": "12:00", "end": "18:00", "period": "super_peak"},
                {"start": "18:00", "end": "00:00", "period": "off_peak"},
            ],
        },
    ],
)
rates = tou.build_tariff_rate(
    period_costs=[
        {"season": "summer", "period": "off_peak", "cost": 1.0},
        {"season": "summer", "period": "super_peak", "cost": 5.0},
    ],
    season_strategy=season,
)
plan = tou.build_tariff_plan(profile, rates)
print(plan.pricing_context(datetime(2025, 7, 1, 13, 0)))
```
