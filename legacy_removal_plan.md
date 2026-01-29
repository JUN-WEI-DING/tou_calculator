# Legacy API Removal Plan

**Status:** Pre-release cleanup  
**Target:** Remove all deprecated/legacy code before first public release  
**Rationale:** No existing users to break, cleaner codebase from day one

---

## 📋 Items to Remove

### 1. `tariff.py` - Legacy Class and Dependencies

#### 1.1 Main Deprecated Class
- **Class:** `TaipowerTariffs` (Lines ~580-620)
- **Impact:** High - exported in `__all__`
- **Dependencies:** None now (TariffJSONLoader import already removed ✅)

#### 1.2 Hardcoded Constants
```python
_RESIDENTIAL_SUMMER_START = (6, 1)      # Line ~470
_RESIDENTIAL_SUMMER_END = (9, 30)       # Line ~471
_HIGH_VOLTAGE_SUMMER_START = (5, 16)   # Line ~527
_HIGH_VOLTAGE_SUMMER_END = (10, 15)    # Line ~528
```

#### 1.3 Hardcoded Schedule Objects
```python
_ALL_DAY_OFF_PEAK                           # Line ~467
_res_simple_two_stage_summer_weekday        # Line ~474
_res_simple_two_stage_nonsummer_weekday     # Line ~481
_hv_two_stage_summer_weekday                # Line ~530
_hv_two_stage_nonsummer_weekday             # Line ~536
_hv_two_stage_summer_saturday               # Line ~545
_hv_two_stage_nonsummer_saturday            # Line ~551
```

#### 1.4 Factory Functions
```python
_create_residential_simple_2_tier()   # Lines ~491-506
_create_residential_non_tou()         # Lines ~509-524
_create_high_voltage_two_stage()      # Lines ~561-576
_make_slot()                          # Lines ~461-464 (helper)
```

---

### 2. `rates.py` - Legacy Methods

#### 2.1 Methods to Remove
```python
TariffJSONLoader.get_residential_simple_rate()      # Lines 58-80
TariffJSONLoader.get_high_voltage_2_tier_rate()     # Lines 82-83 (stub!)
TariffJSONLoader.get_residential_non_tou_rate()     # Lines 99-115
```

**Note:** Keep `get_plan_data()`, `load()`, `_find_plan()` - used by modern code.

---

### 3. `__init__.py` - Public API

#### 3.1 Function to Remove
```python
create_tariff_factory()  # Around line 50-59
```
~~STATUS: Already removed - function does not exist in codebase~~

#### 3.2 Exports to Remove from `__all__`
```python
"TaipowerTariffs",
"create_tariff_factory",  # (if present)
```
~~STATUS: Already removed - not in __all__~~

---

### 4. Tests - Update or Remove

#### 4.1 Files to Update
- `tests/test_tariff.py` - Uses `TaipowerTariffs`
- `tests/test_entry.py` - Uses `TaipowerTariffs`

**Action:** Rewrite to use `TariffFactory`.

---

### 5. Documentation

#### 5.1 Files to Update
- `docs/api_zh.md` - Mentions `TaipowerTariffs`

---

## 🔄 Migration Example

### Before (Legacy)
```python
from tou_calculator import TaipowerTariffs

tariffs = TaipowerTariffs(calendar)
plan = tariffs.get_residential_simple_2_tier_plan()
```

### After (Modern)
```python
from tou_calculator import TariffFactory

factory = TariffFactory(calendar=calendar)
plan = factory.create_plan("residential_simple_2_tier")
```

---

## ✅ Execution Checklist

### Phase 1: Preparation ✅
- [x] ~~Create backup branch~~ (Not needed - pre-release)
- [ ] Run baseline tests: `pytest`

### Phase 2: Update Tests
- [ ] Update `tests/test_tariff.py`
- [ ] Update `tests/test_entry.py`
- [ ] Verify: `pytest tests/test_tariff.py tests/test_entry.py`

### Phase 3: Remove Code
**tariff.py:**
- [x] Remove `TariffJSONLoader` import ✅ (Already done!)
- [ ] Remove `TaipowerTariffs` class (~580-620)
- [ ] Remove `_create_*` functions (~491-576)
- [ ] Remove hardcoded schedules (~467-551)
- [ ] Remove hardcoded constants (~470-528)
- [ ] Remove `_make_slot()` (~461-464)
- [ ] Remove from `__all__`

**rates.py:**
- [ ] Remove 3 legacy methods (58-115)
- [ ] Clean up unused imports

**__init__.py:**
- [x] Remove `create_tariff_factory()` ~~Already removed - function does not exist~~
- [x] Remove exports from `__all__` ~~Already removed - not in __all__~~

### Phase 4: Documentation
- [ ] Update `docs/api_zh.md`
- [ ] Update `README.md` (if needed)

### Phase 5: Verification
- [ ] `pytest` (full suite)
- [ ] `pytest --cov` (coverage)
- [ ] `mypy src/tou_calculator`
- [ ] `ruff check src/tou_calculator`
- [ ] `git grep -i "TaipowerTariffs"`
- [x] `git grep -i "create_tariff_factory"` ~~No references found - already cleaned~~

### Phase 6: Finalize
- [ ] Commit: `git commit -m "Remove legacy API"`
- [ ] Delete this plan file

---

## 🎯 Benefits

- **~241 lines** removed
- Single source of truth (`plans.json`)
- No technical debt
- Cleaner API surface

---

## 📝 Quick Commands

```bash
# Run tests
pytest tests/test_tariff.py tests/test_entry.py -v

# Check for references
git grep -i "TaipowerTariffs"
git grep "get_residential_simple_rate"

# Full verification
pytest && mypy src/tou_calculator && ruff check src/tou_calculator
```
