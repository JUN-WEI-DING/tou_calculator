from datetime import date, datetime

import pandas as pd
import pytest

from tou_calculator import (
    InvalidUsageInput,
    monthly_breakdown,
    period_context,
    plan,
    plan_details,
    pricing_context,
)
from tou_calculator.calendar import TaiwanCalendar
from tou_calculator.tariff import PeriodType, SeasonType, get_period


def _calendar_with_cache(tmp_path) -> TaiwanCalendar:
    cache_file = tmp_path / "2025.json"
    cache_file.write_text("[]", encoding="utf-8")
    return TaiwanCalendar(cache_dir=tmp_path)


def test_residential_simple_2_tier_periods(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    tariff_plan = plan("residential_simple_2_tier", calendar_instance=calendar)

    dt_peak = datetime(2025, 7, 15, 10, 0)
    dt_off_peak = datetime(2025, 7, 13, 10, 0)

    peak_result = get_period(dt_peak, tariff_plan.profile)
    off_peak_result = get_period(dt_off_peak, tariff_plan.profile)
    # Result can be either the enum or its value
    assert peak_result in (PeriodType.PEAK, PeriodType.PEAK.value)
    assert off_peak_result in (PeriodType.OFF_PEAK, PeriodType.OFF_PEAK.value)


def test_high_voltage_2_tier_plan_costs(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    tariff_plan = plan("high_voltage_2_tier", calendar_instance=calendar)

    usage = pd.Series(
        [1.0, 2.0],
        index=pd.DatetimeIndex([date(2025, 7, 15), date(2025, 7, 16)]),
    )
    costs = tariff_plan.calculate_costs(usage)
    assert len(costs) == 1
    assert (costs >= 0).all()


def test_monthly_breakdown_tou(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    index = pd.DatetimeIndex(
        [
            datetime(2025, 7, 15, 10, 0),
            datetime(2025, 7, 15, 23, 0),
        ]
    )
    usage = pd.Series([1.0, 2.0], index=index)
    result = monthly_breakdown(
        usage,
        "residential_simple_2_tier",
        calendar_instance=calendar,
    )

    assert list(result.columns) == ["month", "season", "period", "usage_kwh", "cost"]
    assert result["usage_kwh"].sum() == usage.sum()
    result_with_shares = monthly_breakdown(
        usage,
        "residential_simple_2_tier",
        include_shares=True,
        calendar_instance=calendar,
    )
    assert list(result_with_shares.columns) == [
        "month",
        "season",
        "period",
        "usage_kwh",
        "cost",
        "usage_share",
        "cost_share",
    ]


def test_monthly_breakdown_tiered(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    index = pd.DatetimeIndex(
        [
            datetime(2025, 7, 1, 10, 0),
            datetime(2025, 7, 2, 10, 0),
        ]
    )
    usage = pd.Series([3.0, 5.0], index=index)
    result = monthly_breakdown(
        usage,
        "residential_non_tou",
        calendar_instance=calendar,
    )

    assert list(result.columns) == ["month", "season", "period", "usage_kwh", "cost"]
    assert set(result["period"]) == {"tiered"}


def test_period_context_details(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    dt = datetime(2025, 7, 15, 10, 0)
    context = period_context(
        dt,
        "residential_simple_2_tier",
        calendar_instance=calendar,
    )

    assert context["season"] == SeasonType.SUMMER
    assert context["day_type"] == "weekday"
    assert context["period"] == PeriodType.PEAK


def test_plan_details_schema(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    details = plan_details(
        "residential_simple_2_tier",
        calendar_instance=calendar,
    )

    assert "profile" in details
    assert "rates" in details
    assert details["profile"]["schedules"]
    assert details["rates"]["period_costs"]


def test_pricing_context_single_basic(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    dt = datetime(2025, 7, 15, 10, 0)
    result = pricing_context(
        dt,
        "residential_simple_2_tier",
        usage=1.0,
        calendar_instance=calendar,
    )

    assert result["season"] == SeasonType.SUMMER.value
    assert result["period"] == PeriodType.PEAK.value
    assert result["rate"] is not None
    assert result["cost"] == result["rate"]


def test_pricing_context_details(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    dt = datetime(2025, 7, 15, 10, 0)
    result = pricing_context(
        dt,
        "residential_simple_2_tier",
        include_details=True,
        calendar_instance=calendar,
    )

    assert "context" in result
    assert "rate_details" in result
    assert "profile_details" in result


def test_pricing_context_index_basic(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    index = pd.DatetimeIndex(
        [
            datetime(2025, 7, 15, 10, 0),
            datetime(2025, 7, 15, 23, 0),
        ]
    )
    usage = pd.Series([1.0, 2.0], index=index)
    result = pricing_context(
        index,
        "residential_simple_2_tier",
        usage=usage,
        calendar_instance=calendar,
    )

    assert list(result.columns) == ["season", "period", "rate", "cost"]
    assert (result["cost"] >= 0).all()


def test_pricing_context_tiered_no_usage(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    dt = datetime(2025, 7, 1, 10, 0)
    result = pricing_context(
        dt,
        "residential_non_tou",
        calendar_instance=calendar,
    )

    assert result["rate"] is None
    assert result["cost"] is None


def test_pricing_context_tiered_with_usage_error(tmp_path) -> None:
    calendar = _calendar_with_cache(tmp_path)
    dt = datetime(2025, 7, 1, 10, 0)
    with pytest.raises(InvalidUsageInput):
        pricing_context(
            dt,
            "residential_non_tou",
            usage=1.0,
            calendar_instance=calendar,
        )
