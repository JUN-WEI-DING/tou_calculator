# plans.json Summary

Version: 20251001

## Definitions

### Seasons
- seasons:
  - summer: 06-01 ~ 09-30
  - non_summer: 10-01 ~ 05-31
- seasons_high_voltage:
  - summer: 05-16 ~ 10-15
  - non_summer: 10-16 ~ 05-15

### Periods
- peak, semi_peak, off_peak, flat

### Day types
- weekday, saturday, sunday_holiday

## Plans

| id | name | type | category | season_strategy | notes |
| --- | --- | --- | --- | --- | --- |
| residential_non_tou | 表燈(住商)非時間電價-住宅用 | TIERED | lighting | seasons | tiers:6 |
| lighting_non_business_tiered | 表燈(住商)非時間電價-住宅以外非營業用 | TIERED | lighting | seasons | tiers:6 |
| lighting_business_tiered | 表燈(住商)非時間電價-營業用 | TIERED | lighting | seasons | tiers:5 |
| residential_simple_2_tier | 簡易型時間電價-二段式 | TOU | lighting | seasons | basic_fee, rates:4, schedules:10, over_2000_kwh_surcharge |
| residential_simple_3_tier | 簡易型時間電價-三段式 | TOU | lighting | seasons | basic_fee, rates:5, schedules:12, over_2000_kwh_surcharge |
| lighting_standard_2_tier | 標準型時間電價-二段式 | TOU | lighting | seasons | basic_fees, rates:10, schedules:14 |
| lighting_standard_3_tier | 標準型時間電價-三段式 | TOU | lighting | seasons | basic_fees, rates:11, schedules:16 |
| low_voltage_power | 低壓電力-非時間電價 | NON_TOU | low_voltage | seasons | basic_fees, rates:2 |
| low_voltage_2_tier | 低壓電力-二段式時間電價 | TOU | low_voltage | seasons | basic_fees, rates:10, schedules:14 |
| low_voltage_three_stage | 低壓電力-三段式時間電價 | TOU | low_voltage | seasons | basic_fees, rates:11, schedules:16 |
| low_voltage_ev | 低壓-電動車充換電設施電價 | TOU | low_voltage | seasons | basic_fees, rates:8, schedules:10 |
| high_voltage_power | 高壓電力 | TOU | high_voltage | seasons_high_voltage | basic_fees, rates:10, schedules:14 |
| high_voltage_2_tier | 高壓電力-二段式時間電價 | TOU | high_voltage | seasons_high_voltage | basic_fees, rates:10, schedules:14 |
| high_voltage_three_stage | 高壓電力-三段式時間電價 | TOU | high_voltage | seasons_high_voltage | basic_fees, rates:11, schedules:16 |
| high_voltage_batch | 高壓-批次生產時間電價 | TOU | high_voltage | seasons_high_voltage | basic_fees, rates:10, schedules:14 |
| high_voltage_ev | 高壓-電動車充換電設施電價 | TOU | high_voltage | seasons_high_voltage | basic_fees, rates:8, schedules:10 |
| extra_high_voltage_power | 特高壓電力 | TOU | extra_high_voltage | seasons_high_voltage | basic_fees, rates:10, schedules:14 |
| extra_high_voltage_2_tier | 特高壓電力-二段式時間電價 | TOU | extra_high_voltage | seasons_high_voltage | basic_fees, rates:10, schedules:14 |
| extra_high_voltage_three_stage | 特高壓電力-三段式時間電價 | TOU | extra_high_voltage | seasons_high_voltage | basic_fees, rates:11, schedules:16 |
| extra_high_voltage_batch | 特高壓-批次生產時間電價 | TOU | extra_high_voltage | seasons_high_voltage | basic_fees, rates:10, schedules:14 |
