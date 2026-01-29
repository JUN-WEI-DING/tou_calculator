"""tou_calculator API usage examples with Chinese annotations."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

import tou_calculator as tou


def _sample_usage(start: datetime, periods: int, freq_minutes: int) -> pd.Series:
    index = pd.date_range(start=start, periods=periods, freq=f"{freq_minutes}min")
    values = [1.0 + (i % 3) * 0.25 for i in range(periods)]
    return pd.Series(values, index=index)


def main() -> None:
    cache_dir = Path(".cache")

    # taiwan_calendar: 建立臺灣假日行事曆，cache_dir 可指定快取位置
    # api_timeout 可調整 API 請求超時秒數
    calendar = tou.taiwan_calendar(cache_dir=cache_dir)
    # is_holiday: 判斷日期是否為假日（可傳 date 或 datetime）
    print("is_holiday:", tou.is_holiday(datetime(2025, 7, 13), calendar=calendar))

    # available_plans: 取得支援方案名稱列表
    print("available_plans:", tou.available_plans())

    # residential_simple_2_tier_plan / high_voltage_2_tier_plan
    # / residential_non_tou_plan:
    # 直接取得各方案的 TariffPlan
    simple_plan = tou.residential_simple_2_tier_plan(calendar)
    tou.high_voltage_2_tier_plan(calendar)
    non_tou_plan = tou.residential_non_tou_plan(calendar)

    # plan: 以方案名稱取得 TariffPlan
    plan_by_name = tou.plan("residential_simple_2_tier", calendar_instance=calendar)
    print("plan name:", plan_by_name.profile.name)

    # period_at: 以方案名稱取得時間點的時段型別
    dt = datetime(2025, 7, 15, 10, 0)
    print(
        "period_at:",
        tou.period_at(dt, "residential_simple_2_tier", calendar_instance=calendar),
    )
    # get_period: 直接用 profile 查時段型別
    print("get_period:", tou.get_period(dt, simple_plan.profile))

    # period_context: 回傳 season/day_type/period
    print(
        "period_context:",
        tou.period_context(dt, "residential_simple_2_tier", calendar_instance=calendar),
    )

    # pricing_context: 回傳 season/period/rate/cost
    # （時間電價方案可用 usage 計算逐時費用）
    print(
        "pricing_context:",
        tou.pricing_context(
            dt,
            "residential_simple_2_tier",
            usage=1.0,
            calendar_instance=calendar,
        ),
    )

    # pricing_context + include_details=True: 附上完整費率與時段結構
    print(
        "pricing_context_details:",
        tou.pricing_context(
            dt,
            "residential_simple_2_tier",
            include_details=True,
            calendar_instance=calendar,
        ),
    )

    # plan_details: 回傳完整方案結構（時段表與費率表）
    print(
        "plan_details:",
        tou.plan_details("high_voltage_2_tier", calendar_instance=calendar),
    )

    # calculate_costs: 以 TariffPlan 計算每月費用
    # （usage 必須是 Series，index 為 DatetimeIndex）
    usage = _sample_usage(datetime(2025, 7, 15, 16, 0), periods=4, freq_minutes=30)
    print("calculate_costs:", tou.calculate_costs(usage, simple_plan))
    # costs: 以方案名稱計算每月費用（內部會建立 TariffPlan）
    print(
        "costs:",
        tou.costs(usage, "residential_simple_2_tier", calendar_instance=calendar),
    )
    # monthly_breakdown: 以方案名稱輸出每月用電/費用，按 season/period 彙總
    print(
        "monthly_breakdown:\n",
        tou.monthly_breakdown(
            usage, "residential_simple_2_tier", calendar_instance=calendar
        ),
    )
    # monthly_breakdown + include_shares: 附上各時段佔比
    print(
        "monthly_breakdown_shares:\n",
        tou.monthly_breakdown(
            usage,
            "residential_simple_2_tier",
            include_shares=True,
            calendar_instance=calendar,
        ),
    )

    # pricing_context（DatetimeIndex 版本）: 回傳 DataFrame（season/period）
    index = pd.date_range(datetime(2025, 7, 15, 0, 0), periods=3, freq="12H")
    print(
        "pricing_context_index:\n",
        tou.pricing_context(
            index,
            "residential_simple_2_tier",
            calendar_instance=calendar,
        ),
    )

    # Non-TOU（分級電價）範例
    non_tou_usage = _sample_usage(
        datetime(2025, 7, 1, 0, 0), periods=5, freq_minutes=60
    )
    print("non_tou_costs:", tou.calculate_costs(non_tou_usage, non_tou_plan))

    # period_context（DatetimeIndex 版本）: 回傳 DataFrame（season/day_type/period）
    start = datetime(2025, 7, 15)
    window = pd.date_range(start, start + timedelta(hours=6), freq="2H")
    print(
        "period_context_index:\n",
        tou.period_context(window, "high_voltage_2_tier", calendar_instance=calendar),
    )

    # 自訂方案範例：自訂行事曆 + 自訂時段 + 自訂費率
    custom_calendar = tou.custom_calendar()
    day_types = tou.WeekdayDayTypeStrategy(custom_calendar)
    season = tou.TaiwanSeasonStrategy((6, 1), (9, 30))
    custom_profile = tou.build_tariff_profile(
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
    custom_rates = tou.build_tariff_rate(
        period_costs=[
            {"season": "summer", "period": "off_peak", "cost": 1.0},
            {"season": "summer", "period": "super_peak", "cost": 5.0},
        ],
        season_strategy=season,
    )
    custom_plan = tou.build_tariff_plan(custom_profile, custom_rates)
    print(
        "custom_plan_context:",
        custom_plan.pricing_context(datetime(2025, 7, 1, 13, 0)),
    )


if __name__ == "__main__":
    main()
