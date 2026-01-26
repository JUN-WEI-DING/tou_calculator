# Taiwan TOU Calculator

A small, closed-scope calculator for Taiwan time-of-use (TOU) electricity pricing.
This package provides fixed Taiwan rules and Taipower plans with a simple
function-based API.

## Install

```bash
pip install tou-calculator
```

## Quickstart

```python
from datetime import datetime
import pandas as pd
import tou_calculator as tou

calendar = tou.taiwan_calendar()
plan = tou.high_voltage_two_stage_plan(calendar)

print(tou.is_holiday(datetime(2025, 7, 13), calendar=calendar))
print(tou.get_period(datetime(2025, 7, 15, 10, 0), plan.profile))
print(tou.pricing_context(datetime(2025, 7, 15, 10, 0), "residential_simple_two_stage", usage=1.0))

usage = pd.Series(
    [1.2, 0.8, 1.5],
    index=pd.to_datetime(
        ["2025-07-15 16:00", "2025-07-15 16:30", "2025-07-15 17:00"]
    ),
)
print(tou.calculate_costs(usage, plan))
```

## API

### `taiwan_calendar(cache_dir=None, api_timeout=10)`
Create a Taiwan holiday calendar instance with API-backed data and local caching.
Use `cache_dir` to control where holiday JSON files are stored.

### `taipower_tariffs(calendar=None, cache_dir=None, api_timeout=10)`
Return a factory that creates Taipower tariff profiles and plans.
If no calendar is provided, a default Taiwan calendar is created.

### `available_plans()`
Return the list of supported plan names:
`high_voltage_two_stage`, `residential_non_tou`, `residential_simple_two_stage`.

### `plan(name, calendar_instance=None, cache_dir=None, api_timeout=10)`
Create a tariff plan by name. Raises `ValueError` if the plan name is unsupported.

### `period_at(target, plan_name, ...)`
Convenience wrapper to return the period type at a datetime for a named plan.

### `costs(usage, plan_name, ...)`
Convenience wrapper to calculate monthly costs for a usage series with a named plan.

### `monthly_breakdown(usage, plan_name, include_shares=False, ...)`
Return monthly usage/cost totals grouped by season and period. Tiered plans
return a single row per month with `period="tiered"`. Set `include_shares=True`
to add `usage_share` and `cost_share` per month.

### `pricing_context(target, plan_name, usage=None, include_details=False, ...)`
Return season/period/rate/cost for a single `datetime` or `pandas.DatetimeIndex`.
Usage-based pricing is only available for time-of-use plans; tiered plans
return `None` for rate/cost and should use `calculate_costs` monthly totals.
When `usage` is omitted, `rate` is returned and `cost` remains `None`.
Set `include_details=True` to attach full rate and schedule metadata.

### `period_context(target, plan_name, ...)`
Return season/day_type/period for a single `datetime` or `pandas.DatetimeIndex`.

### `get_period(target, profile)`
Return the period type for a `datetime` or `pandas.DatetimeIndex`.

### `calculate_costs(usage, plan)`
Calculate monthly costs for a `pandas.Series` of kWh usage.

### `calculate_bill(usage, plan_id, inputs=None, ...)`
Calculate monthly bill totals using `plans.json` rules. Use `BillingInputs`
to pass contract capacities, power factor, or meter settings.

### `calculate_bill_simple(usage, plan_id, ...)`
Convenience wrapper for quick billing without advanced inputs.

### `calculate_bill_breakdown(usage, plan_id, inputs=None, ...)`
Return a detailed billing breakdown with a monthly summary and per-period details.

## Custom plans

You can build custom calendars, day types, schedules, and rates with helper utilities.

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

Notes:
- `build_tariff_profile` accepts `schedules` as a mapping or a list of dicts.
- Each schedule `slot` uses `start`, `end`, and `period`; time format is `"HH:MM"` and `"24:00"` is treated as midnight.
- Period labels can be `PeriodType` or any string (e.g. `"super_peak"`).
- `build_tariff_rate` supports either `period_costs` or `tiered_rates`.
- Use `default_period` in `build_tariff_profile` to set the fallback period when no slot matches.

## Deployment

### Local editable install

```bash
cd tou_calculator
python -m pip install -e .
```

### Build and install a wheel

```bash
cd tou_calculator
python -m pip install build
python -m build
python -m pip install dist/tou_calculator-0.1.0-py3-none-any.whl
```

### Runtime notes

- Holiday data is fetched on demand from the public Taiwan holiday dataset.
- Cached JSON files are stored under the user cache directory, unless `cache_dir` is provided.
- If the API is unavailable, the calendar falls back to static holidays.

## Data sources and licensing

- Taipower tariff data is derived from the public tariff tables and bundled under `src/tou_calculator/data/`.
- Holiday data is fetched from the TaiwanCalendar dataset at runtime and cached locally.
- Please review upstream data sources for any applicable terms before redistribution.

## Notes

- Holiday data is fetched from the public Taiwan holiday dataset and cached
  locally. If the API is unavailable, a static fallback is used.
