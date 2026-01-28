from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

import tou_calculator as tou


@pytest.fixture
def offline_calendar(tmp_path):
    """
    Returns a TaiwanCalendar instance that is forced offline.
    
    We patch _HolidayFetcher.fetch to raise an exception, which triggers
    the internal fallback to lunar calendar calculation (offline).
    This prevents tests from hitting GitHub limit or hanging on network.
    """
    with patch("tou_calculator.calendar._HolidayFetcher.fetch", side_effect=RuntimeError("Offline mode")):
        yield tou.taiwan_calendar(cache_dir=tmp_path)


def test_calculate_bill_basic_fee(offline_calendar) -> None:
    index = pd.to_datetime(["2025-07-15 10:00", "2025-07-15 23:00"])
    usage = pd.Series([1.0, 2.0], index=index)
    result = tou.calculate_bill_simple(
        usage,
        "residential_simple_2_tier",
        calendar_instance=offline_calendar,
    )

    assert list(result.columns) == [
        "energy_cost",
        "basic_cost",
        "surcharge",
        "adjustment",
        "total",
    ]
    assert result["basic_cost"].iloc[0] == 75.0
    assert (result["total"] >= result["energy_cost"] + result["basic_cost"]).all()


def test_calculate_bill_minimum_usage_rule(offline_calendar) -> None:
    index = pd.to_datetime([datetime(2025, 7, 1, 0, 0)])
    usage = pd.Series([0.0], index=index)
    inputs = tou.BillingInputs(
        meter_phase="single",
        meter_voltage_v=110,
        meter_ampere=10,
    )
    result = tou.calculate_bill(
        usage,
        "residential_non_tou",
        inputs=inputs,
        calendar_instance=offline_calendar,
    )

    assert result["energy_cost"].iloc[0] > 0


def test_calculate_bill_two_month_cycle(offline_calendar) -> None:
    index = pd.to_datetime(["2025-07-01 00:00", "2025-08-01 00:00"])
    usage = pd.Series([10.0, 10.0], index=index)
    result = tou.calculate_bill_simple(
        usage,
        "residential_non_tou",
        calendar_instance=offline_calendar,
    )
    assert len(result.index) == 1


def test_calculate_bill_breakdown(offline_calendar) -> None:
    index = pd.to_datetime(["2025-07-15 10:00", "2025-07-15 23:00"])
    usage = pd.Series([1.0, 2.0], index=index)
    breakdown = tou.calculate_bill_breakdown(
        usage,
        "residential_simple_2_tier",
        calendar_instance=offline_calendar,
    )

    assert {"summary", "details", "basic_details", "adjustment_details"} <= set(
        breakdown.keys()
    )
    summary = breakdown["summary"]
    details = breakdown["details"]
    basic_details = breakdown["basic_details"]
    adjustment_details = breakdown["adjustment_details"]
    assert "total" in summary.columns
    assert {"period", "season", "period_type", "usage_kwh", "energy_cost"} <= set(
        details.columns
    )
    assert {"period", "label", "quantity", "rate", "cost"} <= set(basic_details.columns)
    if not adjustment_details.empty:
        assert {"period", "type", "amount"} <= set(adjustment_details.columns)
