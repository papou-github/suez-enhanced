"""Regression tests for complete-period consumption calculations."""
import importlib.util
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest

root = Path(__file__).resolve().parents[1] / "custom_components/suez_enhanced"
package = ModuleType("suez_testpkg")
package.__path__ = [str(root)]
sys.modules["suez_testpkg"] = package
for name in ("history", "consumption"):
    spec = importlib.util.spec_from_file_location(f"suez_testpkg.{name}", root / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from suez_testpkg.consumption import consumption_summary


def measures(days, today):
    return [
        SimpleNamespace(date=today - timedelta(days=n), volume=100, index=None)
        for n in days
    ]


class ConsumptionTests(unittest.TestCase):
    def test_complete_week(self):
        result = consumption_summary(measures(range(2, 9), date(2026, 10, 19)), date(2026, 10, 19), 5)
        self.assertEqual(result["consumption_7d_liters"], 700)
        self.assertEqual(result["average_daily_liters"], 100)

    def test_missing_day_is_not_zero(self):
        result = consumption_summary(measures([2, 3, 4, 5, 7, 8], date(2026, 10, 19)), date(2026, 10, 19), 5)
        self.assertIsNone(result["consumption_7d_liters"])

    def test_month_cost(self):
        today = date(2026, 10, 19)
        result = consumption_summary(measures(range(2, 19), today), today, 5)
        self.assertEqual(result["consumption_month_liters"], 1700)
        self.assertEqual(result["estimated_month_cost_eur"], 8.5)

    def test_invalid_tariff(self):
        with self.assertRaises(ValueError):
            consumption_summary([], date(2026, 10, 19), -1)

    def test_no_future_or_provisional_days(self):
        today = date(2026, 10, 19)
        result = consumption_summary(measures(range(0, 9), today), today, 5)
        self.assertEqual(result["consumption_7d_liters"], 700)


if __name__ == "__main__":
    unittest.main()
