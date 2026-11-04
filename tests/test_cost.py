"""Cost calculation tests without Home Assistant runtime."""
from datetime import date, timedelta
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from types import SimpleNamespace
import sys
import types
import unittest

root = Path(__file__).resolve().parents[1] / "custom_components" / "suez_enhanced"
pkg = types.ModuleType("suez_enhanced")
pkg.__path__ = [str(root)]
sys.modules.setdefault("suez_enhanced", pkg)
for name in ("history", "consumption"):
    spec = spec_from_file_location(f"suez_enhanced.{name}", root / f"{name}.py")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
from suez_enhanced.consumption import consumption_summary


class CostTests(unittest.TestCase):
    def test_costs_and_projection(self):
        today = date(2026, 11, 4)
        measures = [SimpleNamespace(date=today-timedelta(days=d), volume=1000, index=None) for d in range(2, 10)]
        result = consumption_summary(measures, today, 4.5)
        self.assertEqual(result["estimated_7d_cost_eur"], 31.5)
        self.assertEqual(result["estimated_annual_cost_eur"], 1642.5)
        self.assertIsNone(result["estimated_yesterday_cost_eur"])

    def test_missing_days_not_zero(self):
        today = date(2026, 11, 4)
        measures = [SimpleNamespace(date=today-timedelta(days=2), volume=1000, index=None)]
        result = consumption_summary(measures, today, 4.5)
        self.assertIsNone(result["estimated_7d_cost_eur"])
        self.assertIsNone(result["estimated_annual_cost_eur"])

    def test_zero_price_disables_cost(self):
        today = date(2026, 11, 4)
        measures = [SimpleNamespace(date=today-timedelta(days=d), volume=1000, index=None) for d in range(1, 10)]
        result = consumption_summary(measures, today, 0)
        self.assertIsNone(result["estimated_yesterday_cost_eur"])
        self.assertIsNone(result["estimated_month_cost_eur"])


if __name__ == "__main__":
    unittest.main()
