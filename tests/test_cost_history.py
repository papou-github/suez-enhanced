"""Regression tests for ApexCharts cost history."""
import importlib.util
from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest

root = Path(__file__).resolve().parents[1] / "custom_components/suez_enhanced"
package = ModuleType("suez_chart_tests")
package.__path__ = [str(root)]
sys.modules[package.__name__] = package
for name in ("history", "cost_history"):
    spec = importlib.util.spec_from_file_location(f"{package.__name__}.{name}", root / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from suez_chart_tests.cost_history import cost_history


def reading(day, liters):
    return SimpleNamespace(date=date.fromisoformat(day), volume=liters, index=None)


class CostHistoryTests(unittest.TestCase):
    def test_zero_liters_and_cumulative(self):
        result = cost_history([reading("2026-01-01", 100), reading("2026-01-02", 0)], date(2026, 1, 4), 10)
        self.assertEqual(result["daily_cost_history"], [["2026-01-01", 1.0], ["2026-01-02", 0.0]])
        self.assertEqual(result["cumulative_cost_history"], [["2026-01-01", 1.0], ["2026-01-02", 1.0]])

    def test_missing_day_not_filled_and_cumulative_stops(self):
        result = cost_history([reading("2026-01-01", 100), reading("2026-01-03", 200)], date(2026, 1, 5), 10)
        self.assertEqual(result["daily_cost_history"], [["2026-01-01", 1.0], ["2026-01-03", 2.0]])
        self.assertEqual(result["cumulative_cost_history"], [["2026-01-01", 1.0]])

    def test_provisional_days_excluded(self):
        result = cost_history([reading("2026-01-01", 100), reading("2026-01-02", 200)], date(2026, 1, 3), 10)
        self.assertEqual(result["daily_cost_history"], [["2026-01-01", 1.0]])

    def test_zero_tariff_no_chart(self):
        self.assertEqual(cost_history([], date(2026, 1, 3), 0)["daily_cost_history"], [])

    def test_year_rollover(self):
        result = cost_history([reading("2025-12-31", 500), reading("2026-01-01", 100)], date(2026, 1, 3), 10)
        self.assertEqual(result["daily_cost_history"], [["2026-01-01", 1.0]])


if __name__ == "__main__":
    unittest.main()
