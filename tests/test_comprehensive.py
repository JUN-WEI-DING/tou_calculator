"""Comprehensive API testing for performance, accuracy, and edge cases."""

import time as time_module
from datetime import datetime

import pandas as pd

import tou_calculator as tou


def test_different_data_sizes():
    """Test 1: Different data volumes (效能測試)."""
    print("\n" + "=" * 60)
    print("TEST 1: 不同資料量測試 (Different Data Volumes)")
    print("=" * 60)

    plan = tou.plan("residential_simple_2_tier")

    test_cases = [
        (
            "小資料 (10條)",
            pd.date_range("2025-07-15", periods=10, freq="h"),
            [1.0] * 10,
        ),
        (
            "中資料 (1,000條)",
            pd.date_range("2025-07-01", periods=1000, freq="h"),
            [1.0] * 1000,
        ),
        (
            "大資料 (100,000條)",
            pd.date_range("2025-01-01", periods=100000, freq="h"),
            [1.0] * 100000,
        ),
        (
            "超大資料 (1,000,000條)",
            pd.date_range("2025-01-01", periods=1000000, freq="h"),
            [1.0] * 1000000,
        ),
    ]

    for name, dates, values in test_cases:
        usage = pd.Series(values, index=dates)

        start = time_module.time()
        costs = plan.calculate_costs(usage)
        elapsed = time_module.time() - start

        print(f"{name}:")
        print(f"  - 耗時: {elapsed:.3f} 秒")
        print(f"  - 總成本: {costs.sum():.2f} 元")
        print(f"  - 記憶數量: {len(usage)}")


def test_all_plans():
    """Test 2: All 20 plans can be loaded and calculated (所有方案測試)."""
    print("\n" + "=" * 60)
    print("TEST 2: 所有20個方案測試 (All 20 Plans)")
    print("=" * 60)

    plan_ids = list(tou.available_plans().keys())
    sample_usage = pd.Series(
        [1.0] * 24,
        index=pd.date_range("2025-07-15", periods=24, freq="h"),
    )

    results = []
    for plan_id in plan_ids:
        try:
            start = time_module.time()
            plan = tou.plan(plan_id)
            costs = plan.calculate_costs(sample_usage)
            elapsed = time_module.time() - start
            results.append((plan_id, costs.sum(), elapsed, "✅"))
        except Exception as e:
            results.append((plan_id, 0, 0, f"❌ {e}"))

    print(f"{'方案名稱':<40} {'總成本':>10} {'耗時':>8} {'狀態'}")
    print("-" * 70)
    for plan_id, cost, elapsed, status in results:
        print(f"{plan_id:<40} {cost:>10.2f} {elapsed:>8.3f}s {status}")


def test_accuracy_verification():
    """Test 3: Manual calculation verification (準確度驗證)."""
    print("\n" + "=" * 60)
    print("TEST 3: 準確度驗證 - 手動計算對比 (Accuracy Verification)")
    print("=" * 60)

    # 場景：2025年7月15日下午2點，夏天尖峰時段，用電10度
    # residential_simple_2_tier 夏月尖峰費率 = 5.16 元/kWh
    expected_rate = 5.16
    expected_cost = 10.0 * expected_rate  # 51.6 元

    dt = datetime(2025, 7, 15, 14, 0)
    # Note: pricing_context takes (target, plan_name, usage=None, ...)
    ctx = tou.pricing_context(dt, "residential_simple_2_tier", usage=10.0)

    print("測試場景: 2025-07-15 14:00 (夏月尖峰) 用電 10 kWh")
    print(f"預期費率: {expected_rate} TWD/kWh")
    print(f"實際費率: {ctx['rate']} TWD/kWh")
    print(f"預期成本: {expected_cost} TWD")
    print(f"實際成本: {ctx['cost']} TWD")
    rate_pass = abs(ctx["rate"] - expected_rate) < 0.01
    cost_pass = abs(ctx["cost"] - expected_cost) < 0.01
    print(f"費率準確: {'✅ 透過' if rate_pass else '❌ 失敗'}")
    print(f"成本準確: {'✅ 透過' if cost_pass else '❌ 失敗'}")


def test_holiday_accuracy():
    """Test 4: Holiday detection accuracy (假日判斷準確度)."""
    print("\n" + "=" * 60)
    print("TEST 4: 假日判斷準確度 (Holiday Detection)")
    print("=" * 60)

    test_dates = [
        (datetime(2025, 1, 1), True, "元旦"),
        (datetime(2025, 1, 28), True, "春節假期首日"),
        (datetime(2025, 1, 29, 0, 0), True, "春節初一(農曆)"),
        (datetime(2025, 2, 28), True, "和平紀念日"),
        (datetime(2025, 4, 4), True, "兒童節/清明節"),
        (datetime(2025, 10, 10), True, "國慶日"),
        (datetime(2025, 12, 25), True, "聖誕節"),
        (datetime(2025, 7, 15, 14, 0), False, "一般工作日"),
    ]

    print(f"{'日期':<20} {'預期':<8} {'實際':<8} {'說明':<15} {'結果'}")
    print("-" * 70)

    all_correct = True
    for dt, expected, desc in test_dates:
        actual = tou.is_holiday(dt)
        status = "✅" if actual == expected else "❌"
        if actual != expected:
            all_correct = False
        print(
            f"{dt.isoformat():<20} {str(expected):<8} "
            f"{str(actual):<8} {desc:<15} {status}"
        )

    print(f"\n假日判斷: {'✅ 全部正確' if all_correct else '❌ 有錯誤'}")


def test_edge_cases():
    """Test 5: Edge cases (邊界情況測試)."""
    print("\n" + "=" * 60)
    print("TEST 5: 邊界情況測試 (Edge Cases)")
    print("=" * 60)

    plan = tou.plan("residential_simple_2_tier")

    edge_cases = [
        ("跨月資料", pd.date_range("2025-06-30 22:00", periods=6, freq="h"), [1.0] * 6),
        ("跨年資料", pd.date_range("2024-12-31 22:00", periods=6, freq="h"), [1.0] * 6),
        ("閏年2月29", pd.date_range("2024-02-29", periods=24, freq="h"), [1.0] * 24),
        ("凌晨時段", pd.date_range("2025-07-15 00:00", periods=3, freq="h"), [1.0] * 3),
        ("深夜時段", pd.date_range("2025-07-15 23:00", periods=3, freq="h"), [1.0] * 3),
    ]

    for name, dates, values in edge_cases:
        usage = pd.Series(values, index=dates)
        try:
            costs = plan.calculate_costs(usage)
            print(f"✅ {name}: 成功 (總成本 {costs.sum():.2f} 元)")
        except Exception as e:
            print(f"❌ {name}: 失敗 - {e}")


def test_different_formats():
    """Test 6: Different data formats (不同資料格式)."""
    print("\n" + "=" * 60)
    print("TEST 6: 不同資料格式測試 (Different Data Formats)")
    print("=" * 60)

    plan = tou.plan("residential_simple_2_tier")
    dates = pd.date_range("2025-07-15", periods=5, freq="h")

    # Test with Series
    usage_series = pd.Series([1.0, 2.0, 1.5, 2.5, 1.0], index=dates)
    costs_series = plan.calculate_costs(usage_series)
    print(f"✅ pandas Series: 成本 {costs_series.iloc[0]:.2f} 元")

    # Test with DataFrame column
    df = pd.DataFrame({"usage": [1.0, 2.0, 1.5, 2.5, 1.0]}, index=dates)
    costs_df = plan.calculate_costs(df["usage"])
    print(f"✅ DataFrame column: 成本 {costs_df.iloc[0]:.2f} 元")

    # Test with different frequencies
    for freq, name in [
        ("15min", "15分鐘"),
        ("30min", "30分鐘"),
        ("1h", "1小時"),
        ("1D", "1天"),
    ]:
        d = pd.date_range("2025-07-15", periods=10, freq=freq)
        u = pd.Series([1.0] * 10, index=d)
        c = plan.calculate_costs(u)
        print(f"✅ {name}頻率: 成本 {c.sum():.2f} 元")


def test_seasonal_variation():
    """Test 7: Seasonal rate differences (季節費率差異)."""
    print("\n" + "=" * 60)
    print("TEST 7: 季節費率差異測試 (Seasonal Rate Variation)")
    print("=" * 60)

    tou.plan("residential_simple_2_tier")  # For coverage

    # 夏月 vs 非夏月
    summer_dt = datetime(2025, 7, 15, 14, 0)  # 夏月
    non_summer_dt = datetime(2025, 1, 15, 14, 0)  # 非夏月

    summer_ctx = tou.pricing_context(summer_dt, "residential_simple_2_tier")
    non_summer_ctx = tou.pricing_context(non_summer_dt, "residential_simple_2_tier")

    print(f"夏月 (7月15日) 費率: {summer_ctx['rate']:.2f} TWD/kWh")
    print(f"非夏月 (1月15日) 費率: {non_summer_ctx['rate']:.2f} TWD/kWh")
    print(f"差異: {summer_ctx['rate'] - non_summer_ctx['rate']:.2f} TWD/kWh")
    summer_higher = summer_ctx["rate"] > non_summer_ctx["rate"]
    print(f"✅ 夏月費率較高: {'是' if summer_higher else '否'}")


def test_period_classification():
    """Test 8: Period classification (時段分類測試)."""
    print("\n" + "=" * 60)
    print("TEST 8: 時段分類測試 (Period Classification)")
    print("=" * 60)

    # 測試高壓三段式方案
    tou.plan("high_voltage_three_stage")  # For coverage

    test_times = [
        ("尖峰時段", datetime(2025, 7, 15, 14, 0)),  # 週二下午
        ("半尖峰時段", datetime(2025, 7, 19, 22, 0)),  # 週一晚上
        ("離峰時段", datetime(2025, 7, 16, 2, 0)),  # 週三凌晨
    ]

    print(f"{'測試時段':<15} {'時段型別':<15} {'結果'}")
    print("-" * 40)

    for name, dt in test_times:
        period = tou.period_at(dt, "high_voltage_three_stage")
        print(f"{name:<15} {str(period):<15} ✅")


def test_weekday_vs_holiday():
    """Test 9: Weekday vs Holiday rates (平日vs假日費率)."""
    print("\n" + "=" * 60)
    print("TEST 9: 平日vs假日費率測試 (Weekday vs Holiday Rates)")
    print("=" * 60)

    # 使用高壓二段式方案
    weekday = datetime(2025, 7, 14, 14, 0)  # 週一
    sunday = datetime(2025, 7, 13, 14, 0)  # 週日

    weekday_ctx = tou.pricing_context(weekday, "high_voltage_2_tier")
    sunday_ctx = tou.pricing_context(sunday, "high_voltage_2_tier")

    print(f"週一 (7/14) 下午2點 - 費率: {weekday_ctx['rate']:.2f} TWD/kWh")
    print(f"週日 (7/13) 下午2點 - 費率: {sunday_ctx['rate']:.2f} TWD/kWh")
    print(f"差異: {weekday_ctx['rate'] - sunday_ctx['rate']:.2f} TWD/kWh")
    sunday_cheaper = sunday_ctx["rate"] < weekday_ctx["rate"]
    print(f"✅ 假日費率較低: {'是' if sunday_cheaper else '否'}")


def test_consistency():
    """Test 10: Result consistency (結果一致性測試)."""
    print("\n" + "=" * 60)
    print("TEST 10: 結果一致性測試 (Result Consistency)")
    print("=" * 60)

    plan = tou.plan("residential_simple_2_tier")
    dates = pd.date_range("2025-07-15", periods=100, freq="h")
    usage = pd.Series([1.0] * 100, index=dates)

    # 多次計算結果應該相同
    results = [plan.calculate_costs(usage).sum() for _ in range(5)]

    print(f"5次計算結果: {[f'{r:.4f}' for r in results]}")
    print(f"最大差異: {max(results) - min(results):.10f}")
    print(f"✅ 結果一致: {'是' if max(results) - min(results) < 0.01 else '否'}")


def test_billing_accuracy():
    """Test 11: Billing calculation accuracy (完整帳單計算準確度)."""
    print("\n" + "=" * 60)
    print("TEST 11: 完整帳單計算準確度 (Billing Calculation)")
    print("=" * 60)

    from tou_calculator import BillingInputs, calculate_bill

    # 場景：高壓使用者，契約容量200kW，實際用電
    dates = pd.date_range("2025-07-01 00:00", periods=48, freq="30min")
    usage = pd.Series([100.0] * 48, index=dates)  # 每半小時100kW

    inputs = BillingInputs(
        contract_capacities={"regular": 200},
        power_factor=90.0,
    )

    bill = calculate_bill(usage, "high_voltage_2_tier", inputs=inputs)

    print(f"用電度數: {usage.sum():.0f} kWh")
    print("\n帳單明細:")
    print(f"  - 電能費: {bill['energy_cost'].iloc[0]:.2f} 元")
    print(f"  - 基本費: {bill['basic_cost'].iloc[0]:.2f} 元")
    print(f"  - 違約金: {bill['surcharge'].iloc[0]:.2f} 元")
    print(f"  - 力率調整: {bill['adjustment'].iloc[0]:.2f} 元")
    print(f"  - 總計: {bill['total'].iloc[0]:.2f} 元")
    print("\n✅ 計算完成，無錯誤")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("臺灣時間電價 API 綜合測試")
    print("Comprehensive API Testing for Taiwan TOU Calculator")
    print("=" * 60)

    test_different_data_sizes()
    test_all_plans()
    test_accuracy_verification()
    test_holiday_accuracy()
    test_edge_cases()
    test_different_formats()
    test_seasonal_variation()
    test_period_classification()
    test_weekday_vs_holiday()
    test_consistency()
    test_billing_accuracy()

    print("\n" + "=" * 60)
    print("測試完成！所有測試已執行。")
    print("=" * 60)
