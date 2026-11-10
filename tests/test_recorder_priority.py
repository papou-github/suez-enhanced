"""Regression tests for Recorder-first annual cost merge."""
import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "suez_enhanced"
tree = ast.parse((ROOT / "year_merge.py").read_text())
fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
          and node.name == "merge_year_readings")
namespace = {"SimpleNamespace": SimpleNamespace}
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
             "<year_merge>", "exec"), namespace)
merge = namespace["merge_year_readings"]


def reading(day, liters):
    return SimpleNamespace(day=date.fromisoformat(day), liters=liters, meter_index_liters=None)


class YearMergeTests(unittest.TestCase):
    def test_recorder_wins_on_overlap_even_when_api_is_zero(self):
        recorder = [reading("2026-10-10", 113), reading("2026-10-11", 253)]
        api = [reading("2026-10-10", 0), reading("2026-10-11", 113)]
        merged = merge(recorder, api)
        self.assertEqual([(r.date.isoformat(), r.volume) for r in merged],
                         [("2026-10-10", 113), ("2026-10-11", 253)])

    def test_api_fills_missing_days_without_overwriting_recorder(self):
        recorder = [reading("2026-10-10", 113)]
        api = [reading("2026-10-09", 0), reading("2026-10-10", 0),
               reading("2026-10-11", 113)]
        merged = merge(recorder, api)
        self.assertEqual([(r.date.isoformat(), r.volume) for r in merged],
                         [("2026-10-09", 0), ("2026-10-10", 113),
                          ("2026-10-11", 113)])


if __name__ == "__main__":
    unittest.main()
