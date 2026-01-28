# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-29

### Added
- Initial release of Taiwan TOU Calculator
- Support for all 20 Taipower tariff plans
  - Residential: non-TOU, simple 2-tier, simple 3-tier
  - Lighting: non-business tiered, business tiered, standard 2/3-tier
  - Low Voltage: power, 2-tier, 3-stage, EV
  - High Voltage: power, 2-tier, 3-stage, batch production, EV
  - Extra High Voltage: power, 2-tier, 3-stage, batch production
- Flexible plan name matching (English ID, Chinese, bilingual, with/without spaces)
- Taiwan holiday calendar with API fallback
- Energy cost calculation with monthly aggregation
- Full bill calculation (energy cost, basic fee, penalty, power factor adjustment)
- Demand penalty calculation based on 15-minute peak demand
- Custom plan builders for creating custom tariff schedules
- No-pandas convenience functions (`calculate_bill_from_list`, `calculate_bill_from_dict`)
- Bilingual API documentation (English/Chinese)

### Testing
- 364 tests across 12 test modules
- 104 production readiness tests covering:
  - Security & input validation
  - Multilingual & encoding support
  - Extreme scenarios (leap years, century transitions)
  - Data type compatibility
  - API compatibility
  - Concurrency & race conditions
  - Resource management
  - Documentation examples
  - Boundary values
  - Error recovery
  - Performance benchmarks
  - Version compatibility
- Accuracy validation against Taipower official rates
- Stress tests (5M+ records, concurrent access, memory stability)
- End-to-end tests simulating real-world scenarios

### Documentation
- Comprehensive README with bilingual quick start tutorial
- API documentation (English and Chinese)
- Calculation logic background with formulas
- Performance benchmarks and optimization tips

### Development Status
- Python 3.9-3.13 support
- CI/CD with GitHub Actions (tests on Python 3.9, 3.10, 3.11, 3.12, 3.13)
- Pre-commit hooks for code quality (ruff, mypy)
- MIT License

[0.1.0]: https://github.com/JUN-WEI-DING/tou_calculator/releases/tag/v0.1.0
