"""Parameterized tests for all tariff plans in plans.json."""

from __future__ import annotations

import pandas as pd
import pytest

import tou_calculator as tou
from tou_calculator.factory import TariffFactory


class TestAllPlans:
    """Parameterized tests to verify all plans can be loaded and evaluated."""

    @pytest.fixture
    def sample_usage(self) -> pd.Series:
        """Create sample usage data for testing."""
        return pd.Series(
            [1.0] * 48,
            index=pd.date_range("2024-07-15", periods=48, freq="30min"),
        )

    def test_available_plans_not_empty(self) -> None:
        """Verify that plans are available."""
        plans = list(tou.available_plans().keys())
        assert len(plans) > 0
        assert isinstance(plans, (list, tuple))

    @pytest.mark.parametrize("plan_id", list(tou.available_plans().keys()))
    def test_plan_can_be_loaded(self, plan_id: str, tmp_path) -> None:
        """Test that each plan can be loaded without errors."""
        # Use empty cache to avoid network calls
        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        plan = tou.plan(plan_id, cache_dir=tmp_path)
        assert plan is not None
        assert plan.profile is not None
        assert plan.rates is not None

    @pytest.mark.parametrize("plan_id", list(tou.available_plans().keys()))
    def test_plan_has_valid_profile(self, plan_id: str, tmp_path) -> None:
        """Test that each plan has a valid profile structure."""
        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        plan = tou.plan(plan_id, cache_dir=tmp_path)
        profile = plan.profile

        assert profile.name is not None
        assert len(profile.name) > 0

        # Check that profile can describe itself
        description = profile.describe()
        assert "name" in description
        assert "seasons" in description
        assert "day_types" in description
        assert "schedules" in description

    @pytest.mark.parametrize("plan_id", list(tou.available_plans().keys()))
    def test_plan_evaluate_context(self, plan_id: str, tmp_path) -> None:
        """Test that each plan can evaluate context for a datetime index."""
        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        plan = tou.plan(plan_id, cache_dir=tmp_path)
        index = pd.date_range("2024-07-15", periods=24, freq="1h")

        context = plan.profile.evaluate(index)
        assert isinstance(context, pd.DataFrame)
        assert "season" in context.columns
        assert "day_type" in context.columns
        assert "period" in context.columns
        assert len(context) == 24

    @pytest.mark.parametrize("plan_id", list(tou.available_plans().keys()))
    def test_plan_calculate_costs(
        self, plan_id: str, tmp_path, sample_usage: pd.Series
    ) -> None:
        """Test that each plan can calculate costs for sample usage."""
        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        plan = tou.plan(plan_id, cache_dir=tmp_path)
        costs = plan.calculate_costs(sample_usage)

        assert isinstance(costs, pd.Series)
        assert (costs >= 0).all()  # All costs should be non-negative

    @pytest.mark.parametrize("plan_id", list(tou.available_plans().keys()))
    def test_plan_monthly_breakdown(
        self, plan_id: str, tmp_path, sample_usage: pd.Series
    ) -> None:
        """Test that each plan can provide monthly breakdown."""
        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        plan = tou.plan(plan_id, cache_dir=tmp_path)
        breakdown = plan.monthly_breakdown(sample_usage)

        assert isinstance(breakdown, pd.DataFrame)
        assert "month" in breakdown.columns
        assert "season" in breakdown.columns
        assert "usage_kwh" in breakdown.columns
        assert "cost" in breakdown.columns

    @pytest.mark.parametrize("plan_id", list(tou.available_plans().keys()))
    def test_plan_pricing_context(self, plan_id: str, tmp_path) -> None:
        """Test that each plan can provide pricing context."""
        from datetime import datetime

        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        plan = tou.plan(plan_id, cache_dir=tmp_path)

        # Test with datetime
        context = plan.pricing_context(datetime(2024, 7, 15, 10, 0))
        assert "season" in context
        assert "period" in context

    @pytest.mark.parametrize("plan_id", list(tou.available_plans().keys()))
    def test_plan_describe(self, plan_id: str, tmp_path) -> None:
        """Test that each plan can describe itself."""
        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        plan = tou.plan(plan_id, cache_dir=tmp_path)
        description = plan.describe()

        assert isinstance(description, dict)
        assert "profile" in description
        assert "rates" in description


class TestTariffFactory:
    """Tests for the TariffFactory class."""

    def test_factory_list_plans(self) -> None:
        """Test that factory can list all plans."""
        factory = TariffFactory()
        plans = factory.list_plans()

        assert len(plans) > 0
        assert isinstance(plans, tuple)

    def test_factory_create_plan(self, tmp_path) -> None:
        """Test that factory can create a plan."""
        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        factory = TariffFactory()
        plan = factory.create_plan("residential_simple_2_tier")

        assert plan is not None
        assert plan.profile is not None
        assert plan.rates is not None

    def test_factory_create_invalid_plan(self, tmp_path) -> None:
        """Test that factory raises KeyError for invalid plan."""
        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        factory = TariffFactory()
        with pytest.raises(KeyError, match="Plan not found"):
            factory.create_plan("nonexistent_plan")

    def test_factory_create_classmethod(self, tmp_path) -> None:
        """Test TariffFactory.create() class method."""
        cache_file = tmp_path / "2024.json"
        cache_file.write_text("[]", encoding="utf-8")

        plan = TariffFactory.create("residential_simple_2_tier")
        assert plan is not None
