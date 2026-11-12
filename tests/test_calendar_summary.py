"""Read-only yearly summaries: gaps, leap years, and archive precedence."""
import ast
from datetime import date
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "custom_components" / "suez_enhanced" / "recorder_history.py"
# Isolate the pure function to run without Home Assistant installed.
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "summarize_calendar_year")
module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
from importlib.util import spec_from_file_location, module_from_spec
spec = spec_from_file_location("standalone_tariffs_calendar", SOURCE.with_name("tariffs.py"))
tariff_module = module_from_spec(spec)
spec.loader.exec_module(tariff_module)
namespace = {"TariffSchedule": tariff_module.TariffSchedule}
exec(compile(module, str(SOURCE), "exec"), namespace)
summarize = namespace["summarize_calendar_year"]


class CalendarSummaryTests(unittest.TestCase):
    def test_partial_year_never_claimed_complete(self):
        result = summarize({date(2026, 1, 1): 1000, date(2026, 1, 3): 500}, 2026, 2.5)
        self.assertEqual(result["recorded_days"], 2)
        self.assertFalse(result["complete"])
        self.assertEqual(result["m3"], 1.5)
        self.assertEqual(result["estimated_cost_eur"], 3.75)

    def test_leap_year_has_366_expected_days(self):
        result = summarize({date(2024, 2, 29): 250}, 2024, 0)
        self.assertEqual(result["expected_days"], 366)
        self.assertIsNone(result["estimated_cost_eur"])

    def test_no_days_returns_none(self):
        self.assertIsNone(summarize({date(2025, 1, 1): 100}, 2026, 3.0))


if __name__ == "__main__":
    unittest.main()
