import warnings
from datetime import datetime

import pandas as pd
import pytest

import taipower_tou as tou


@pytest.fixture
def empty_cache_file(tmp_path):
    """Create an empty cache file to avoid network calls."""
    cache_file = tmp_path / "2025.json"
    cache_file.write_text("[]", encoding="utf-8")
    return tmp_path


def test_calculate_bill_basic_fee(empty_cache_file) -> None:
    index = pd.to_datetime(["2025-07-15 10:00", "2025-07-15 23:00"])
    usage = pd.Series([1.0, 2.0], index=index)
    result = tou.calculate_bill_simple(
        usage,
        "residential_simple_2_tier",
        cache_dir=empty_cache_file,
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


def test_calculate_bill_minimum_usage_rule(empty_cache_file) -> None:
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
        cache_dir=empty_cache_file,
    )

    assert result["energy_cost"].iloc[0] > 0


def test_calculate_bill_two_month_cycle(empty_cache_file) -> None:
    index = pd.to_datetime(["2025-07-01 00:00", "2025-08-01 00:00"])
    usage = pd.Series([10.0, 10.0], index=index)
    inputs = tou.BillingInputs(
        meter_phase="single",
        meter_voltage_v=110,
        meter_ampere=10,
    )
    result = tou.calculate_bill(
        usage,
        "residential_non_tou",
        inputs=inputs,
        cache_dir=empty_cache_file,
    )
    assert len(result.index) == 1


def test_calculate_bill_breakdown(empty_cache_file) -> None:
    index = pd.to_datetime(["2025-07-15 10:00", "2025-07-15 23:00"])
    usage = pd.Series([1.0, 2.0], index=index)
    breakdown = tou.calculate_bill_breakdown(
        usage,
        "residential_simple_2_tier",
        cache_dir=empty_cache_file,
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


def test_calculate_bill_rejects_negative_usage(empty_cache_file) -> None:
    usage = pd.Series(
        [1.0, -0.5],
        index=pd.to_datetime(["2025-07-15 10:00", "2025-07-15 11:00"]),
    )
    with pytest.raises(tou.InvalidUsageInput):
        tou.calculate_bill(
            usage, "residential_simple_2_tier", cache_dir=empty_cache_file
        )


def test_calculate_bill_rejects_nan_usage(empty_cache_file) -> None:
    usage = pd.Series(
        [1.0, float("nan")],
        index=pd.to_datetime(["2025-07-15 10:00", "2025-07-15 11:00"]),
    )
    with pytest.raises(tou.InvalidUsageInput):
        tou.calculate_bill(
            usage, "residential_simple_2_tier", cache_dir=empty_cache_file
        )


def test_calculate_bill_rejects_infinite_usage(empty_cache_file) -> None:
    usage = pd.Series(
        [1.0, float("inf")],
        index=pd.to_datetime(["2025-07-15 10:00", "2025-07-15 11:00"]),
    )
    with pytest.raises(tou.InvalidUsageInput):
        tou.calculate_bill(
            usage, "residential_simple_2_tier", cache_dir=empty_cache_file
        )


def test_calculate_bill_rejects_unsorted_usage(empty_cache_file) -> None:
    usage = pd.Series(
        [1.0, 2.0],
        index=pd.to_datetime(["2025-07-15 11:00", "2025-07-15 10:00"]),
    )
    with pytest.raises(tou.InvalidUsageInput):
        tou.calculate_bill(
            usage, "residential_simple_2_tier", cache_dir=empty_cache_file
        )


def test_calculate_bill_breakdown_rejects_invalid_usage(empty_cache_file) -> None:
    usage = pd.Series(
        [1.0, -0.5],
        index=pd.to_datetime(["2025-07-15 10:00", "2025-07-15 11:00"]),
    )
    with pytest.raises(tou.InvalidUsageInput):
        tou.calculate_bill_breakdown(
            usage, "residential_simple_2_tier", cache_dir=empty_cache_file
        )


def test_for_residential_does_not_warn_unknown_basic_fee(empty_cache_file) -> None:
    usage = pd.Series([1.0], index=pd.to_datetime(["2025-07-15 10:00"]))
    inputs = tou.BillingInputs.for_residential(phase="single", voltage=110, ampere=10)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        tou.calculate_bill(
            usage,
            "residential_simple_2_tier",
            inputs=inputs,
            cache_dir=empty_cache_file,
        )
    assert not any("Unknown keys in basic_fee_inputs" in str(w.message) for w in record)
