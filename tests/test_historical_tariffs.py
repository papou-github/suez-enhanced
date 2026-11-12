"""Historical tariff regression tests without importing Home Assistant."""
import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "suez_enhanced"


def load_functions(filename, names, namespace):
    tree = ast.parse((ROOT / filename).read_text())
    nodes = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 filename, "exec"), namespace)


tariffs = {"date": date, "bisect_right": __import__("bisect").bisect_right,
           "isfinite": __import__("math").isfinite}
load_functions("tariffs.py", {"parse_tariffs", "TariffSchedule"}, tariffs)
TariffSchedule = tariffs["TariffSchedule"]


class TariffTests(unittest.TestCase):
    def test_effective_dates_and_legacy_fallback(self):
        schedule = TariffSchedule(8.40, "2026-07-01;8,75\n2025-01-01;7.92")
        self.assertEqual(schedule.price(date(2024, 12, 31)), 8.40)
        self.assertEqual(schedule.price(date(2025, 1, 1)), 7.92)
        self.assertEqual(schedule.price(date(2026, 6, 30)), 7.92)
        self.assertEqual(schedule.price(date(2026, 7, 1)), 8.75)
        self.assertEqual(schedule.cost({date(2026, 6, 30): 1000,
                                        date(2026, 7, 1): 1000}), 16.67)

    def test_duplicate_and_invalid_values(self):
        for history in ("2026-01-01;8\n2026-01-01;9",
                        "2026-02-30;8", "2026-01-01;-1",
                        "2026-01-01;nan", "2026-01-01 8"):
            with self.subTest(history=history), self.assertRaises(ValueError):
                TariffSchedule(8.4, history)

    def test_no_history_keeps_old_flat_cost(self):
        schedule = TariffSchedule(8.4)
        self.assertEqual(round(schedule.cost({date(2026, 1, 1): 78438}), 2), 658.88)

    def test_repricing_does_not_change_volumes(self):
        liters = {date(2026, 6, 30): 150, date(2026, 7, 1): 200}
        before = dict(liters)
        self.assertNotEqual(TariffSchedule(8.4).cost(liters),
                            TariffSchedule(8.4, "2026-07-01;9").cost(liters))
        self.assertEqual(liters, before)


if __name__ == "__main__":
    unittest.main()
